from fastapi import APIRouter, Depends
from typing import Optional

from app.store import CANDIDATES, ASSESSMENTS
from app.auth_dependency import get_current_recruiter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/recruiter")
def recruiter_dashboard(
    recruiter_slug: Optional[str] = None,
    role: Optional[str] = None,
    _recruiter: dict = Depends(get_current_recruiter),
):
    """Both filters are optional and combinable. With neither set, this
    returns the full team-wide pipeline (matching Greenhouse's default
    unfiltered candidate list) - filtering is an explicit UI choice,
    not something tied to who's logged in."""
    rows = []

    for candidate in CANDIDATES.list_candidates(role_applied_for=role, recruiter_slug=recruiter_slug):
        candidate_id = candidate["candidate_id"]
        assessment = ASSESSMENTS.get(candidate_id)

        # Join each competency to the actual question that was asked
        # and the candidate's real transcribed answer, so the full
        # scorecard shows question + answer + AI evidence together
        # instead of needing to check a separate recordings panel.
        assessment_questions = candidate.get("assessment_questions", [])
        assessment_progress = candidate.get("assessment_progress", {})

        question_by_competency = {
            q["competency_key"]: q["question"] for q in assessment_questions
        }
        transcript_by_competency = {}
        pre_recording_seconds_by_competency = {}
        for entry in assessment_progress.values():
            comp_key = entry.get("competency_key")
            if comp_key:
                transcript_by_competency[comp_key] = entry.get("transcript", "")
                pre_recording_seconds_by_competency[comp_key] = entry.get("pre_recording_seconds", 0)

        competencies_enriched = []
        for c in (assessment.get("competencies", []) if assessment else []):
            enriched = dict(c)
            enriched["question"] = question_by_competency.get(c["key"], "")
            enriched["transcript"] = transcript_by_competency.get(c["key"], "")
            enriched["pre_recording_seconds"] = pre_recording_seconds_by_competency.get(c["key"], 0)
            competencies_enriched.append(enriched)

        rows.append(
            {
                "candidate_id": candidate_id,
                "full_name": candidate.get("full_name"),
                "email": candidate.get("email"),
                "current_location": candidate.get("current_location"),
                "preferred_location": candidate.get("preferred_location"),
                "years_of_experience": candidate.get("years_of_experience"),
                "notice_period_days": candidate.get("notice_period_days"),
                "expected_salary": candidate.get("expected_salary"),
                "fixed_salary": candidate.get("fixed_salary"),
                "variable_pay": candidate.get("variable_pay"),
                "availability_slots": candidate.get("availability_slots"),
                "candidate_availability": candidate.get("candidate_availability"),
                "confirmed_interview": candidate.get("confirmed_interview"),
                "call_mode": candidate.get("call_mode"),
                "resume_filename": candidate.get("resume_filename"),
                "resume_original_name": candidate.get("resume_original_name"),
                "recruiter_name": candidate.get("recruiter_name"),
                "recruiter_slug": candidate.get("recruiter_slug"),
                "role_applied_for": candidate.get("role_applied_for"),
                "source_channel": candidate.get("source_channel"),
                "tab_switch_count": candidate.get("tab_switch_count", 0),
                "fullscreen_exit_count": candidate.get("fullscreen_exit_count", 0),
                "focus_loss_count": candidate.get("focus_loss_count", 0),
                "stage": candidate.get("stage"),
                "rejection_reason": candidate.get("rejection_reason"),
                "overall_score": assessment.get("overall_score") if assessment else None,
                "recommendation": assessment.get("recommendation") if assessment else None,
                "top_strengths": [
                    c["label"]
                    for c in assessment.get("competencies", [])[:3]
                ] if assessment else [],
                "competencies": competencies_enriched,
                "notes": assessment.get("notes") if assessment else None,
            }
        )

    return {"count": len(rows), "candidates": rows}