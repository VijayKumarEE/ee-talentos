"""
Scheduling + self-scheduling email flow.

Two trigger points, matching the roadmap:
1. Recruiter clicks "Shortlist" on a candidate
   -> generate mock recruiter-round slots
   -> "send" (console-log) a self-scheduling email to the candidate
2. Recruiter submits the scorecard with shortlist=True ("Yes")
   -> generate mock panel-round slots
   -> "send" a self-scheduling email to the candidate for the panel round

Candidates then "book" a slot from either round via /scheduling/book.
"""

from fastapi import APIRouter, HTTPException, Depends, Body

from app.schemas import RecruiterReview
from app.store import CANDIDATES
from app.services.scheduling_service import generate_mock_slots, find_slot
from app.services.github_showcase_service import push_candidate_shortlisted, push_recruiter_decision
from app.services.email_service import (
    send_email,
    build_self_scheduling_email,
    build_booking_confirmation_email,
    build_rejection_email,
    build_interview_confirmed_email,
)
from app.auth_dependency import get_current_recruiter
from app.config import ZOOM_MEETING_LINK

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


def _get_candidate_or_404(candidate_id: str) -> dict:
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CANDIDATES[candidate_id]


def _save_candidate(candidate_id: str, candidate: dict) -> None:
    CANDIDATES[candidate_id] = candidate


@router.get("/slots")
def get_slots():
    """Legacy placeholder endpoint - kept for backwards compatibility."""
    return {"slots": []}


@router.post("/shortlist/{candidate_id}")
def shortlist_candidate(candidate_id: str, _recruiter: dict = Depends(get_current_recruiter)):
    """Recruiter clicks 'Shortlist' on the dashboard. Generates recruiter-
    round slots and emails the candidate a self-scheduling link."""
    candidate = _get_candidate_or_404(candidate_id)

    slots = generate_mock_slots(panel="recruiter")

    scheduling = candidate.get("scheduling", {})
    scheduling["recruiter_slots"] = slots
    scheduling["recruiter_booked_slot"] = None
    candidate["scheduling"] = scheduling
    candidate["stage"] = "recruiter_scheduling_sent"
    _save_candidate(candidate_id, candidate)

    push_candidate_shortlisted(candidate)

    email_body = build_self_scheduling_email(
        candidate_name=candidate.get("full_name", "Candidate"),
        round_label="Recruiter Screen",
        slots=slots,
    )
    send_email(
        to=candidate.get("email", "unknown@candidate.local"),
        subject="Schedule your Recruiter Screen interview",
        body=email_body,
    )

    return {
        "message": "Candidate shortlisted. Self-scheduling email sent (see backend console).",
        "candidate_id": candidate_id,
        "stage": candidate["stage"],
        "slots": slots,
    }


@router.post("/reject/{candidate_id}")
def reject_candidate(candidate_id: str, reason: str = "", _recruiter: dict = Depends(get_current_recruiter)):
    """Recruiter's initial post-assessment decision: reject before any
    interview happens. Distinct from the scorecard's 'No' path, which
    is for rejecting *after* a recruiter interview has taken place."""
    candidate = _get_candidate_or_404(candidate_id)

    candidate["stage"] = "rejected"
    candidate["rejection_reason"] = reason
    _save_candidate(candidate_id, candidate)

    email_body = build_rejection_email(
        candidate_name=candidate.get("full_name", "Candidate"),
        role=candidate.get("current_role") or "",
        reason=reason,
    )
    send_email(
        to=candidate.get("email", "unknown@candidate.local"),
        subject="Update on your application",
        body=email_body,
    )

    return {
        "message": "Candidate rejected. Rejection email sent (see backend console).",
        "candidate_id": candidate_id,
        "stage": candidate["stage"],
    }


@router.get("/{candidate_id}/slots")
def get_candidate_slots(candidate_id: str, round: str = "recruiter"):
    """Candidate-facing: fetch the slots offered for a given round
    ('recruiter' or 'panel')."""
    candidate = _get_candidate_or_404(candidate_id)
    scheduling = candidate.get("scheduling", {})

    key = f"{round}_slots"
    slots = scheduling.get(key, [])

    return {"candidate_id": candidate_id, "round": round, "slots": slots}


@router.post("/{candidate_id}/book")
def book_slot(candidate_id: str, slot_id: str, round: str = "recruiter"):
    """Candidate picks a slot from either round."""
    candidate = _get_candidate_or_404(candidate_id)
    scheduling = candidate.get("scheduling", {})

    slots = scheduling.get(f"{round}_slots", [])
    slot = find_slot(slots, slot_id)

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found for this round")

    scheduling[f"{round}_booked_slot"] = slot
    candidate["scheduling"] = scheduling
    candidate["stage"] = f"{round}_interview_scheduled"
    _save_candidate(candidate_id, candidate)

    round_label = "Recruiter Screen" if round == "recruiter" else "Panel Interview"
    email_body = build_booking_confirmation_email(
        candidate_name=candidate.get("full_name", "Candidate"),
        round_label=round_label,
        slot=slot,
    )
    send_email(
        to=candidate.get("email", "unknown@candidate.local"),
        subject=f"Interview confirmed: {round_label}",
        body=email_body,
    )

    return {
        "message": "Slot booked and confirmation email sent (see backend console).",
        "candidate_id": candidate_id,
        "stage": candidate["stage"],
        "booked_slot": slot,
    }


@router.post("/{candidate_id}/scorecard")
def submit_scorecard(candidate_id: str, review: RecruiterReview, _recruiter: dict = Depends(get_current_recruiter)):
    """Recruiter submits the scorecard. If shortlist=True ('Yes'),
    generates panel-round slots and emails the candidate again."""
    candidate = _get_candidate_or_404(candidate_id)

    candidate["recruiter_review"] = review.model_dump()

    push_recruiter_decision(candidate)

    if review.shortlist:
        slots = generate_mock_slots(panel="panel")

        scheduling = candidate.get("scheduling", {})
        scheduling["panel_slots"] = slots
        scheduling["panel_booked_slot"] = None
        candidate["scheduling"] = scheduling
        candidate["stage"] = "panel_scheduling_sent"
        _save_candidate(candidate_id, candidate)

        email_body = build_self_scheduling_email(
            candidate_name=candidate.get("full_name", "Candidate"),
            round_label="Panel Interview",
            slots=slots,
        )
        send_email(
            to=candidate.get("email", "unknown@candidate.local"),
            subject="Schedule your Panel Interview",
            body=email_body,
        )

        return {
            "message": "Scorecard saved. Candidate advanced - panel scheduling email sent.",
            "candidate_id": candidate_id,
            "stage": candidate["stage"],
            "slots": slots,
        }

    candidate["stage"] = "rejected"
    _save_candidate(candidate_id, candidate)

    return {
        "message": "Scorecard saved. Candidate marked as rejected.",
        "candidate_id": candidate_id,
        "stage": candidate["stage"],
    }


@router.post("/{candidate_id}/confirm-interview")
def confirm_interview(
    candidate_id: str,
    confirmed_time: str = Body(..., embed=True),
    _recruiter: dict = Depends(get_current_recruiter),
):
    """Recruiter-only. Picks one concrete time (read against the
    candidate's own stated availability - see /candidates/{id}/
    availability - though nothing here enforces it came from that
    list, since the recruiter and candidate may have already agreed a
    time some other way, e.g. a quick call) and locks it in. Sends the
    ONE confirmation email in this flow - the candidate isn't asked to
    pick/negotiate anything over email, they're just told the final
    time and where to join. `confirmed_time` is a plain string (e.g.
    "Thu 18 Sep, 11:00 AM IST") rather than a strict datetime, so the
    recruiter can phrase it however reads clearly."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    candidate["confirmed_interview"] = {
        "time": confirmed_time,
        "zoom_link": ZOOM_MEETING_LINK,
    }
    _save_candidate(candidate_id, candidate)

    email_body = build_interview_confirmed_email(
        candidate_name=candidate.get("full_name", "there"),
        role=candidate.get("role_applied_for", ""),
        confirmed_time=confirmed_time,
        zoom_link=ZOOM_MEETING_LINK,
    )
    send_email(
        to=candidate.get("email", "unknown@candidate.local"),
        subject="Your interview is confirmed",
        body=email_body,
    )

    return {
        "message": "Interview confirmed - candidate notified by email.",
        "candidate_id": candidate_id,
        "confirmed_interview": candidate["confirmed_interview"],
    }
