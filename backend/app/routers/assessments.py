import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Depends
from fastapi.responses import FileResponse, RedirectResponse

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
from app.services.github_showcase_service import push_assessment_scored
from app.auth_dependency import get_current_recruiter
from app.providers.storage_provider import get_storage_provider
from app.providers.transcription_provider import get_transcription_provider
from app.config import IS_CLOUD_MODE

router = APIRouter(prefix="/assessment", tags=["assessment"])

# Buildathon MVP scope: the reduced-to-3-questions flow (2 rotated
# technical + 1 consulting) is only built for the two roles with a
# real question bank behind them. Every other role keeps the
# original 5-question flow completely unchanged - no consulting
# question, no rotation - until (if ever) more roles get their own
# real question content the same way DevOps and Backend Engineer did.
ROLES_WITH_CONSULTING_QUESTION = {"operability-engineer", "backend-engineer"}

# LOCAL MODE: recordings on disk under backend/uploaded_recordings/.
# CLOUD MODE: recordings in the Supabase "recordings" bucket, private,
# played back only via short-lived signed URLs.
storage = get_storage_provider()
transcription = get_transcription_provider()


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
def analyze_candidate(payload: CandidateAssessmentRequest, retry: bool = False):
    """Runs AI scoring for a candidate's assessment.

    IMPORTANT - do-not-reprocess guard (handover brief, section 12):
    a candidate/recruiter accidentally hitting this twice (refresh,
    double-submit, retry) must not silently trigger a second paid
    OpenRouter call and must not create a duplicate assessment record.
    If this candidate already has a saved assessment AND the caller
    did not explicitly pass retry=true, the existing result is
    returned as-is - no new LLM call is made, no email is re-sent, and
    the showcase is not re-pushed."""
    if payload.candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    existing_assessment = ASSESSMENTS.get(payload.candidate_id)
    if existing_assessment and not retry:
        return existing_assessment

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
    retry: bool = Body(False),
):
    """Stores the candidate's audio/video recording (disk in LOCAL
    MODE, Supabase Storage in CLOUD MODE) and transcribes it.

    IMPORTANT - do-not-reprocess guard (see handover brief, section 12):
    a candidate refreshing or re-submitting the same question must not
    silently trigger another paid OpenRouter transcription call. If
    this question already has a status of "transcribed" (or is
    currently "transcribing"), the upload is accepted and the file is
    re-saved, but transcription is skipped and the existing transcript
    is kept - UNLESS the caller explicitly passes retry=true, which is
    the only path that re-runs transcription on an already-processed
    recording."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    progress = candidate.get("assessment_progress", {})
    entry = progress.get(question_id, {})

    existing_status = entry.get("transcription_status")
    already_processed = existing_status in ("transcribed", "transcribing") and not retry

    contents = file.file.read()
    storage_ref = storage.save_recording(candidate_id, question_id, contents)

    entry["recording_filename"] = storage_ref
    entry["mode"] = mode

    if already_processed:
        # Keep the existing transcript/status untouched - this is
        # exactly the "don't reprocess" guard: no new transcription
        # call happens here.
        progress[question_id] = entry
        candidate["assessment_progress"] = progress
        CANDIDATES[candidate_id] = candidate
        return {"message": "Recording re-uploaded; using existing transcript", "question_id": question_id}

    entry["transcription_status"] = "transcribing"
    progress[question_id] = entry
    candidate["assessment_progress"] = progress
    CANDIDATES[candidate_id] = candidate

    if IS_CLOUD_MODE:
        local_copy = storage.local_temp_copy(storage_ref, "recordings")
        try:
            transcript = transcription.transcribe(local_copy, mode, candidate_id)
        finally:
            if local_copy.exists():
                local_copy.unlink()
    else:
        file_path = Path(storage.get_recording_path_or_url(storage_ref))
        transcript = transcription.transcribe(file_path, mode, candidate_id)

    candidate = CANDIDATES[candidate_id]
    progress = candidate.get("assessment_progress", {})
    entry = progress.get(question_id, {})
    entry["transcript"] = transcript
    entry["transcription_status"] = "transcribed" if transcript else "failed"
    progress[question_id] = entry
    candidate["assessment_progress"] = progress
    CANDIDATES[candidate_id] = candidate

    return {"message": "Recording uploaded", "question_id": question_id}


@router.get("/recording/{candidate_id}/{question_id}")
def download_recording(candidate_id: str, question_id: str, _recruiter: dict = Depends(get_current_recruiter)):
    """Serves a candidate's recording back for playback (recruiter
    side). LOCAL MODE serves the file directly; CLOUD MODE redirects
    to a short-lived signed URL - still behind get_current_recruiter,
    so only a logged-in recruiter can ever mint one."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    progress = candidate.get("assessment_progress", {})
    entry = progress.get(question_id, {})
    storage_ref = entry.get("recording_filename")

    if not storage_ref:
        raise HTTPException(status_code=404, detail="No recording found for this question")

    if IS_CLOUD_MODE:
        try:
            signed_url = storage.get_recording_path_or_url(storage_ref)
        except Exception:
            raise HTTPException(status_code=404, detail="Recording file missing in storage")
        return RedirectResponse(url=signed_url)

    file_path = Path(storage.get_recording_path_or_url(storage_ref))
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