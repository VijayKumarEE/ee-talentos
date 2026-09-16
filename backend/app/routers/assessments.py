import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Depends
from fastapi.responses import FileResponse

from app.competencies import get_assessment_plan_for_candidate, get_competencies_for_role
from app.schemas import (
    AssessmentQuestionsRequest,
    AssessmentQuestionsResponse,
    AssessmentQuestion,
    CandidateAssessmentRequest,
    CompetencyKey,
)
from app.services.assessment_service import analyze_assessment
from app.question_bank import get_question_for_role_competency
from app.consulting_questions import get_consulting_question_for_candidate
from app.store import CANDIDATES, ASSESSMENTS
from app.services.email_service import (
    send_email,
    build_recruiter_assessment_complete_email,
)
from app.services.transcription_service import transcribe_recording
from app.services.github_showcase_service import push_assessment_scored
from app.auth_dependency import get_current_recruiter

router = APIRouter(prefix="/assessment", tags=["assessment"])

# Buildathon MVP scope: the reduced-to-3-questions flow (2 rotated
# technical + 1 consulting) is only built for the two roles with a
# real question bank behind them. Every other role keeps the
# original 5-question flow completely unchanged - no consulting
# question, no rotation - until (if ever) more roles get their own
# real question content the same way DevOps and Backend Engineer did.
ROLES_WITH_CONSULTING_QUESTION = {"operability-engineer", "backend-engineer"}

# Recordings stored on disk under backend/uploaded_recordings/{candidate_id}/,
# one file per question, so recruiters can actually play them back.
RECORDING_DIR = Path(__file__).resolve().parent.parent.parent / "uploaded_recordings"
RECORDING_DIR.mkdir(exist_ok=True)


@router.post("/questions", response_model=AssessmentQuestionsResponse)
def generate_questions(payload: AssessmentQuestionsRequest):
    if payload.candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # The candidate's role is authoritative from their own application
    # record - not trusted from whatever the frontend happens to send,
    # so a mismatch can't accidentally hand out the wrong question set.
    candidate = CANDIDATES[payload.candidate_id]
    role_slug = candidate.get("role_applied_for", "operability-engineer")

    if role_slug in ROLES_WITH_CONSULTING_QUESTION:
        # Exactly 3 competencies: 2 technical (round-robin rotated) + 1
        # consulting (role-agnostic). See get_assessment_plan_for_candidate
        # for the selection mechanism - this is the single source of truth
        # also used by /analyze, so the two can never disagree about which
        # competencies this candidate's assessment covers.
        role_competencies = get_assessment_plan_for_candidate(role_slug, payload.candidate_id)
    else:
        # Unchanged original behavior - all 5 competencies, no consulting
        # question, for every role outside this buildathon's scope.
        role_competencies = get_competencies_for_role(role_slug)

    # Pulled from a curated bank with round-robin rotation across
    # variants - every candidate for the same role gets a fair mix of
    # questions instead of everyone seeing the exact same ones, which
    # would let candidates share questions and pre-prepare answers.
    questions = []

    for index, competency in enumerate(role_competencies, start=1):
        if competency.key == CompetencyKey.consulting:
            # Role-agnostic - same bank regardless of role, not pulled
            # from the per-role QUESTION_BANK at all.
            _, question_text = get_consulting_question_for_candidate(payload.candidate_id)
        else:
            question_text = get_question_for_role_competency(
                role_slug, competency.key.value, competency.label, payload.candidate_id
            )

        questions.append(
            AssessmentQuestion(
                question_id=f"q{index}",
                competency_key=competency.key,
                question=question_text,
            )
        )

    # IMPORTANT: fetch -> mutate -> re-save.
    # SQLDict.__getitem__ returns a fresh dict read from SQLite each time,
    # so mutating it in place (the old dict-only pattern) would silently
    # be lost. Re-assigning via __setitem__ persists the change.
    candidate["assessment_questions"] = [question.model_dump() for question in questions]
    CANDIDATES[payload.candidate_id] = candidate

    from app.roles import get_role_label

    return AssessmentQuestionsResponse(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        role=get_role_label(role_slug),
        questions=questions,
    )


@router.post("/analyze")
def analyze_candidate(payload: CandidateAssessmentRequest):
    if payload.candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[payload.candidate_id]
    role_slug = candidate.get("role_applied_for", "operability-engineer")

    if role_slug in ROLES_WITH_CONSULTING_QUESTION:
        # Same selection function used by /questions - guarantees scoring
        # covers exactly the 3 competencies this candidate was actually
        # asked about, never the old full set of 5.
        role_competencies = get_assessment_plan_for_candidate(role_slug, payload.candidate_id)
    else:
        role_competencies = get_competencies_for_role(role_slug)

    # Use the REAL transcribed answers stored during recording upload,
    # not whatever placeholder text the frontend sends - this is what
    # actually gets scored, and what gets shown to recruiters later.
    progress = candidate.get("assessment_progress", {})
    real_answers = {}
    for entry in progress.values():
        comp_key = entry.get("competency_key")
        if comp_key:
            real_answers[comp_key] = entry.get("transcript", "") or ""

    if real_answers:
        payload.answers = real_answers

    result = analyze_assessment(payload, role_competencies, role_slug)
    ASSESSMENTS[payload.candidate_id] = result.model_dump()

    # Also flip the candidate's stage so the dashboard (and any future
    # filtering logic) can tell this candidate has been assessed.
    candidate["stage"] = "assessed"
    CANDIDATES[payload.candidate_id] = candidate

    push_assessment_scored(candidate, result.model_dump())

    recruiter_email = candidate.get("recruiter_email")
    recruiter_name = candidate.get("recruiter_name")
    if recruiter_email and recruiter_name:
        email_body = build_recruiter_assessment_complete_email(
            recruiter_name=recruiter_name,
            candidate_name=candidate.get("full_name", "A candidate"),
            overall_score=result.overall_score,
            recommendation=result.recommendation.value,
        )
        send_email(
            to=recruiter_email,
            subject=f"Assessment complete: {candidate.get('full_name', 'A candidate')}",
            body=email_body,
        )

    return result

@router.post("/progress/{candidate_id}")
def save_progress(
    candidate_id: str,
    question_id: str = Body(...),
    competency_key: str = Body(...),
    mode: str = Body(...),
    duration_seconds: int = Body(...),
    tab_switch_count: int = Body(0),
    fullscreen_exit_count: int = Body(0),
    focus_loss_count: int = Body(0),
):
    """Save that a single question has been recorded, so progress
    survives a closed browser/tab. The actual recording file (if the
    candidate's browser successfully uploaded one) is stored separately
    via /assessment/recording/{candidate_id} - this endpoint just
    tracks metadata and stage.

    tab_switch_count, fullscreen_exit_count, and focus_loss_count are
    all running cumulative totals for the whole assessment (not
    per-question) - the frontend sends its latest count each time,
    which we store as-is since they only ever increase. They're
    tracked as three separate signals (not merged into one number) so
    a recruiter can tell them apart on the Shortlist page.

    focus_loss_count specifically catches window-level OS focus loss
    (e.g. Alt-Tab/Cmd-Tab to a different application), which works on
    every device including iPhone Safari - unlike fullscreen
    enforcement, which iPhone Safari doesn't support at all for a
    whole page (only for a <video> element), leaving a real gap that
    tab-switch and fullscreen-exit detection alone can't close on
    that platform."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    progress = candidate.get("assessment_progress", {})

    existing = progress.get(question_id, {})

    progress[question_id] = {
        "competency_key": competency_key,
        "mode": mode,
        "duration_seconds": duration_seconds,
        "recording_filename": existing.get("recording_filename"),
    }

    candidate["assessment_progress"] = progress
    candidate["tab_switch_count"] = tab_switch_count
    candidate["fullscreen_exit_count"] = fullscreen_exit_count
    candidate["focus_loss_count"] = focus_loss_count
    candidate["stage"] = "assessment_in_progress"
    CANDIDATES[candidate_id] = candidate

    return {"message": "Progress saved", "question_id": question_id}


@router.get("/progress/{candidate_id}")
def get_progress(candidate_id: str):
    """Fetch saved progress so the frontend can resume at the right
    question instead of starting over."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    progress = candidate.get("assessment_progress", {})

    return {"candidate_id": candidate_id, "progress": progress}


@router.post("/recording/{candidate_id}")
def upload_recording(
    candidate_id: str,
    question_id: str = Body(...),
    mode: str = Body(...),
    file: UploadFile = File(...),
):
    """Actually stores the candidate's audio/video recording on disk,
    so a recruiter can listen/watch it later - not just metadata."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate_dir = RECORDING_DIR / candidate_id
    candidate_dir.mkdir(exist_ok=True)

    ext = "webm"
    safe_filename = f"{question_id}.{ext}"
    file_path = candidate_dir / safe_filename

    contents = file.file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Transcribe locally (faster-whisper, free, no API key) so scoring
    # can use the candidate's actual words instead of a placeholder.
    # Never blocks/crashes the upload if transcription fails.
    transcript = transcribe_recording(file_path, mode)

    candidate = CANDIDATES[candidate_id]
    progress = candidate.get("assessment_progress", {})
    entry = progress.get(question_id, {})
    entry["recording_filename"] = safe_filename
    entry["transcript"] = transcript
    entry["mode"] = mode
    progress[question_id] = entry
    candidate["assessment_progress"] = progress
    CANDIDATES[candidate_id] = candidate

    return {"message": "Recording uploaded", "question_id": question_id}


@router.get("/recording/{candidate_id}/{question_id}")
def download_recording(candidate_id: str, question_id: str, _recruiter: dict = Depends(get_current_recruiter)):
    """Serves a candidate's recording back for playback (recruiter
    side) - matches the same on-disk pattern as resume download."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    progress = candidate.get("assessment_progress", {})
    entry = progress.get(question_id, {})
    filename = entry.get("recording_filename")

    if not filename:
        raise HTTPException(status_code=404, detail="No recording found for this question")

    file_path = RECORDING_DIR / candidate_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Recording file missing on disk")

    media_type = "video/webm" if entry.get("mode") == "video" else "audio/webm"
    return FileResponse(path=file_path, media_type=media_type)


@router.get("/recordings/{candidate_id}")
def list_recordings(candidate_id: str, _recruiter: dict = Depends(get_current_recruiter)):
    """Returns which questions have an actual playable recording saved,
    including the real transcript and the question that was asked -
    so a recruiter can see exactly what was asked and what the
    candidate said, not just an abstract score."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    progress = candidate.get("assessment_progress", {})
    stored_questions = {
        q["question_id"]: q["question"]
        for q in candidate.get("assessment_questions", [])
    }

    recordings = [
        {
            "question_id": qid,
            "mode": entry.get("mode"),
            "duration_seconds": entry.get("duration_seconds"),
            "transcript": entry.get("transcript", ""),
            "question": stored_questions.get(qid, ""),
        }
        for qid, entry in progress.items()
        if entry.get("recording_filename")
    ]

    return {"candidate_id": candidate_id, "recordings": recordings}