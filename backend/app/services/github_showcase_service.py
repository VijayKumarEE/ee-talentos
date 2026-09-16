"""
Pushes Operability Engineer candidates into the public GitHub Pages
showcase (a static Greenhouse-style replica) so leadership can see the
real pipeline without touching the internal recruiter dashboard.

Four real touchpoints, four pushes - each one attaches its own record
to its own stage, permanently, the way real Greenhouse keeps a stage's
history visible even after a candidate moves past it:

  1. candidates.py -> apply_candidate()
     Candidate applies. Lands on Application Review. No report yet.

  2. assessments.py -> analyze_candidate()
     The AI finishes scoring the recorded assessment. Still sits on
     Application Review (nothing recruiter-facing has happened), but
     the full AI report (not just a number) is now attached to that
     stage for the recruiter to read.

  3. scheduling.py -> shortlist_candidate()
     Recruiter has read the AI report + resume and clicks 'Shortlist'.
     Moves to Screening.

  4. scheduling.py -> submit_scorecard()
     Recruiter has actually spoken with the candidate and records the
     outcome. Only the decision (advance/reject) attaches to the
     Screening stage (that's where the call happened) - the recruiter's
     actual notes/score are PRIVATE recruiting data and are never
     included in this public payload; they stay in Supabase/SQLite,
     reachable only through the authenticated recruiter dashboard. If
     advancing, the candidate also moves to Take Home Test, which shows
     an automatic "assignment sent" status - the real send isn't built
     yet, so this only ever says it was sent, never anything about
     what's in it.

PRIVACY (see also section 15/the CLOUD_DEPLOYMENT.md note): this data
is pushed to a PUBLIC GitHub Pages site. Every payload builder below is
deliberately minimal - name, role, stage, status, and the AI/recruiter
DECISION only. It must never include email, phone, resume, recordings,
transcripts, or recruiter notes/scores - those stay private, in
Supabase/SQLite, behind the authenticated recruiter API only.

Deliberately fire-and-forget throughout: every public function
swallows its own errors and just prints a warning. A GitHub API hiccup
must never break the candidate/recruiter flow - the showcase is a
mirror, not a dependency.

Only pushes candidates whose role_applied_for == "operability-engineer" -
scoped to that one role for the MVP, per plan.
"""

import base64
import json
from datetime import datetime
from typing import Optional

import httpx

from app.config import (
    GITHUB_TOKEN,
    GITHUB_OWNER,
    GITHUB_REPO,
    GITHUB_BRANCH,
    GITHUB_DATA_PATH,
)

SHOWCASE_ROLE_SLUG = "operability-engineer"

API_BASE = "https://api.github.com"


def _configured() -> bool:
    return bool(GITHUB_TOKEN and GITHUB_OWNER and GITHUB_REPO)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def _contents_url() -> str:
    return f"{API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{GITHUB_DATA_PATH}"


def _fetch_current_file() -> tuple[dict, str]:
    """Returns (parsed_json, sha). Raises on any failure - callers catch it."""
    resp = httpx.get(
        _contents_url(),
        headers=_headers(),
        params={"ref": GITHUB_BRANCH},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    sha = payload["sha"]
    raw = base64.b64decode(payload["content"]).decode("utf-8")
    return json.loads(raw), sha


def _push_updated_file(data: dict, sha: str, commit_message: str) -> None:
    body = {
        "message": commit_message,
        "content": base64.b64encode(json.dumps(data, indent=2).encode("utf-8")).decode("ascii"),
        "sha": sha,
        "branch": GITHUB_BRANCH,
    }
    resp = httpx.put(_contents_url(), headers=_headers(), json=body, timeout=15)
    resp.raise_for_status()


def _years_experience(candidate: dict) -> float:
    years = candidate.get("years_of_experience") or 0
    months = candidate.get("months_of_experience") or 0
    return round(years + months / 12, 1)


def _applied_date(candidate: dict) -> str:
    created_at = candidate.get("created_at")
    if created_at:
        return created_at[:10]
    return datetime.utcnow().date().isoformat()


def _today() -> str:
    return datetime.utcnow().date().isoformat()


def _competency_type(key: str) -> str:
    return "consulting" if key == "consulting" else "technical"


def _recommendation_label(recommendation: Optional[str]) -> str:
    return {
        "strong_match": "Strong yes",
        "review": "Review",
        "reject": "No",
    }.get(recommendation, "Review")


def _build_ai_report(assessment: Optional[dict]) -> Optional[dict]:
    """The full AI assessment - every competency's score, level, summary,
    evidence, and follow-up questions. Not just numbers: this is meant
    to stand in for 'the whole text' a recruiter would want to read on
    Application Review, before ever clicking Shortlist."""
    if not assessment:
        return None
    return {
        "type": "ai_report",
        "overall_recommendation": _recommendation_label(assessment.get("recommendation")),
        "overall_score": assessment.get("overall_score", 0),
        "notes": assessment.get("notes", ""),
        "competencies": [
            {
                "name": c["label"],
                "type": _competency_type(c["key"]),
                "score": c["score"],
                "level": c.get("level", ""),
                "summary": c.get("summary", ""),
                "positives": c.get("evidence", {}).get("positive", []),
                "gaps": c.get("evidence", {}).get("gaps", []),
                "risk_flags": c.get("evidence", {}).get("risk_flags", []),
                "follow_up_questions": c.get("follow_up_questions", []),
            }
            for c in assessment.get("competencies", [])
        ],
    }


def _build_recruiter_report(review: dict, advanced: bool) -> dict:
    """PRIVACY: the recruiter's actual notes and score from the
    screening call are private recruiting data - they stay in
    Supabase/SQLite, reachable only through the authenticated recruiter
    dashboard, and must NEVER reach this public payload. Only the
    decision itself (advance/reject) is shown here, since that's
    exactly the "stage progression / application status" the public
    showcase is meant to demonstrate - not the private substance behind
    it."""
    return {
        "type": "recruiter_review",
        "decision": "advance" if advanced else "reject",
    }


def _find_entry(data: dict, candidate_id: str) -> Optional[dict]:
    return next((c for c in data.get("candidates", []) if c["id"] == candidate_id), None)


def _find_stage_entry(entry: dict, stage: str) -> Optional[dict]:
    return next((h for h in entry["stage_history"] if h["stage"] == stage), None)


def _set_stage_detail(entry: dict, stage: str, detail: dict) -> None:
    """Attaches `detail` to the stage_history row for `stage`, creating
    that row (dated today) if the candidate hasn't reached it yet."""
    existing = _find_stage_entry(entry, stage)
    if existing:
        existing["detail"] = detail
    else:
        entry["stage_history"].append({"stage": stage, "date": _today(), "detail": detail})


def push_candidate_applied(candidate: dict) -> None:
    """Call right after a candidate applies (both auto-rejected and
    passed-the-bar cases). Everyone starts at Application Review."""
    if not _configured():
        print("[github_showcase] Not configured (missing token/owner/repo) - skipping push.")
        return
    if candidate.get("role_applied_for") != SHOWCASE_ROLE_SLUG:
        return

    auto_rejected = candidate.get("stage") == "auto_rejected_experience"
    applied_date = _applied_date(candidate)
    total_years = _years_experience(candidate)

    rejection_reason = None
    if auto_rejected:
        rejection_reason = (
            f"Auto-rejected: {total_years:.1f} years of experience, "
            f"below the 7.5 year minimum for this role"
        )

    entry = {
        "id": candidate["candidate_id"],
        "name": candidate.get("full_name", "Unknown Candidate"),
        "current_title": candidate.get("current_role") or "Not specified",
        "current_company": candidate.get("current_organization") or "Not specified",
        # PRIVACY (handover brief, section 15): this data is pushed to a
        # PUBLIC GitHub Pages site. email/phone/resume/recordings/full
        # transcripts/private recruiter notes must NEVER be included here
        # - only the minimum safe demonstration fields. The full private
        # record stays in Supabase/SQLite, reachable only through the
        # authenticated recruiter dashboard.
        "applied_date": applied_date,
        "years_experience": total_years,
        "status": "rejected" if auto_rejected else "active",
        "current_stage": "Application Review",
        "note": rejection_reason if auto_rejected else "Awaiting recruiter review",
        "stage_history": [{
            "stage": "Application Review",
            "date": applied_date,
            "detail": {"type": "status", "message": rejection_reason} if auto_rejected else None,
        }],
    }

    try:
        data, sha = _fetch_current_file()
        candidates = data.setdefault("candidates", [])
        existing_idx = next((i for i, c in enumerate(candidates) if c["id"] == entry["id"]), None)
        if existing_idx is not None:
            candidates[existing_idx] = entry
        else:
            candidates.append(entry)
        _push_updated_file(data, sha, f"Showcase: application from {entry['name']}")
    except Exception as exc:  # noqa: BLE001 - fire-and-forget by design
        print(f"[github_showcase] Failed to push application for {entry['id']}: {exc}")


def push_assessment_scored(candidate: dict, assessment: Optional[dict]) -> None:
    """Call right after analyze_candidate() finishes AI-scoring the
    recorded assessment. Stays on Application Review - just attaches
    the full AI report there and updates the list-view note."""
    if not _configured():
        print("[github_showcase] Not configured (missing token/owner/repo) - skipping push.")
        return
    if candidate.get("role_applied_for") != SHOWCASE_ROLE_SLUG:
        return

    try:
        data, sha = _fetch_current_file()
        entry = _find_entry(data, candidate["candidate_id"])
        if entry is None:
            print(f"[github_showcase] No existing showcase entry for {candidate['candidate_id']}; skipping assessment push.")
            return

        report = _build_ai_report(assessment)
        _set_stage_detail(entry, "Application Review", report)
        entry["note"] = "Assessment complete - awaiting recruiter review"

        _push_updated_file(data, sha, f"Showcase: AI assessment scored for {entry['name']}")
    except Exception as exc:  # noqa: BLE001 - fire-and-forget by design
        print(f"[github_showcase] Failed to push assessment score for {candidate.get('candidate_id')}: {exc}")


def push_candidate_shortlisted(candidate: dict) -> None:
    """Call right after the recruiter clicks 'Shortlist' on the
    dashboard (POST /scheduling/shortlist/{id}) - i.e. after they've
    read the AI report + resume and decided to move to a recruiter
    screen. Moves the showcase entry to Screening."""
    if not _configured():
        print("[github_showcase] Not configured (missing token/owner/repo) - skipping push.")
        return
    if candidate.get("role_applied_for") != SHOWCASE_ROLE_SLUG:
        return

    try:
        data, sha = _fetch_current_file()
        entry = _find_entry(data, candidate["candidate_id"])
        if entry is None:
            print(f"[github_showcase] No existing showcase entry for {candidate['candidate_id']}; skipping shortlist push.")
            return

        entry["status"] = "active"
        entry["current_stage"] = "Screening"
        entry["note"] = "Recruiter screen scheduled"
        if not _find_stage_entry(entry, "Screening"):
            entry["stage_history"].append({"stage": "Screening", "date": _today(), "detail": None})

        _push_updated_file(data, sha, f"Showcase: {entry['name']} shortlisted for recruiter screen")
    except Exception as exc:  # noqa: BLE001 - fire-and-forget by design
        print(f"[github_showcase] Failed to push shortlist for {candidate.get('candidate_id')}: {exc}")


def push_recruiter_decision(candidate: dict) -> None:
    """Call right after submit_scorecard() records the recruiter's
    decision following the actual screening call. The recruiter's
    notes/score attach to Screening (where the call happened). If
    advancing, the candidate also moves to Take Home Test with an
    automatic 'assignment sent' status."""
    if not _configured():
        print("[github_showcase] Not configured (missing token/owner/repo) - skipping push.")
        return
    if candidate.get("role_applied_for") != SHOWCASE_ROLE_SLUG:
        return

    review = candidate.get("recruiter_review") or {}
    advanced = bool(review.get("shortlist"))

    try:
        data, sha = _fetch_current_file()
        entry = _find_entry(data, candidate["candidate_id"])
        if entry is None:
            print(f"[github_showcase] No existing showcase entry for {candidate['candidate_id']}; skipping decision push.")
            return

        _set_stage_detail(entry, "Screening", _build_recruiter_report(review, advanced))

        if advanced:
            entry["status"] = "active"
            entry["current_stage"] = "Take Home Test"
            entry["note"] = "Take-home assignment sent"
            if not _find_stage_entry(entry, "Take Home Test"):
                entry["stage_history"].append({
                    "stage": "Take Home Test",
                    "date": _today(),
                    "detail": {"type": "status", "message": "Take-home assignment sent"},
                })
        else:
            entry["status"] = "rejected"
            entry["note"] = "Not moving forward after recruiter screen"

        _push_updated_file(data, sha, f"Showcase: recruiter decision for {entry['name']}")
    except Exception as exc:  # noqa: BLE001 - fire-and-forget by design
        print(f"[github_showcase] Failed to push recruiter decision for {candidate.get('candidate_id')}: {exc}")
