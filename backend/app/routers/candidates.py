import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request
from fastapi.responses import FileResponse

from app.schemas import CandidateApply
from app.store import CANDIDATES
from app.recruiters import get_recruiter_by_slug
from app.services.email_service import (
    send_email,
    build_recruiter_new_application_email,
)
from app.services.resume_parsing_service import extract_resume_text, extract_candidate_fields
from app.services.github_showcase_service import push_candidate_applied
from app.rate_limiter import check_rate_limit
from app.auth_dependency import get_current_recruiter

router = APIRouter(prefix="/candidates", tags=["candidates"])

# Resumes are stored on disk under backend/uploaded_resumes/, keyed by
# candidate_id, so the recruiter dashboard can link to the original file.
RESUME_DIR = Path(__file__).resolve().parent.parent.parent / "uploaded_resumes"
RESUME_DIR.mkdir(exist_ok=True)

ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/parse-resume")
async def parse_resume(request: Request, file: UploadFile = File(...)):
    """Extracts contact/basic fields from an uploaded resume BEFORE a
    candidate record exists, so the application form can auto-fill
    itself the moment the candidate uploads their resume - before they've
    typed anything else. Deliberately stateless: nothing is saved here,
    the candidate re-submits the same file at the end via the existing
    /{candidate_id}/resume endpoint once their application is created.

    Every field returned is either a confidently-extracted value or
    null - never a guess - so the candidate always reviews and can
    correct anything before submitting."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"resume-parse:{client_ip}", max_attempts=20, window_seconds=60)

    contents = await file.read()
    resume_text = extract_resume_text(contents, file.filename or "")
    fields = extract_candidate_fields(resume_text)

    return fields


@router.post("/apply")
def apply_candidate(payload: CandidateApply):
    candidate_id = str(uuid4())
    candidate = payload.model_dump()
    candidate["candidate_id"] = candidate_id
    candidate["resume_filename"] = None

    # Auto-reject below the minimum experience bar (currently 7.5 years
    # total, i.e. 7 years + 6 months) BEFORE the candidate ever reaches
    # the assessment - they see a generic thank-you page and are never
    # asked to record anything. This is deliberately silent: nothing in
    # the response or the candidate-facing UI states the specific reason,
    # so it isn't treated as a rejection reason to argue with, but the
    # application and its stated experience are still fully saved for
    # recruiter visibility/audit, consistent with how every other
    # rejection in this app is still retained.
    MIN_TOTAL_EXPERIENCE_YEARS = 7.5
    total_years = (payload.years_of_experience or 0) + (payload.months_of_experience or 0) / 12
    auto_rejected = total_years < MIN_TOTAL_EXPERIENCE_YEARS

    candidate["stage"] = "auto_rejected_experience" if auto_rejected else "applied"

    recruiter = get_recruiter_by_slug(payload.recruiter_slug) if payload.recruiter_slug else None
    if recruiter:
        candidate["recruiter_name"] = recruiter["name"]
        candidate["recruiter_email"] = recruiter["email"]
        candidate["recruiter_slug"] = recruiter["slug"]
    else:
        candidate["recruiter_name"] = None
        candidate["recruiter_email"] = None
        candidate["recruiter_slug"] = None

    CANDIDATES[candidate_id] = candidate

    push_candidate_applied(candidate)

    # Don't notify the recruiter for auto-rejected applications - nothing
    # for them to act on, and it would just be noise in their inbox.
    if recruiter and not auto_rejected:
        email_body = build_recruiter_new_application_email(
            recruiter_name=recruiter["name"],
            candidate_name=candidate.get("full_name", "A candidate"),
            role=(f"the {candidate.get('current_role')} role" if candidate.get("current_role") else "an open role"),
        )
        send_email(
            to=recruiter["email"],
            subject=f"New application: {candidate.get('full_name', 'A candidate')}",
            body=email_body,
        )

    return {
        "message": "candidate applied",
        "candidate_id": candidate_id,
        "candidate": candidate,
        "auto_rejected": auto_rejected,
    }


@router.post("/{candidate_id}/resume")
def upload_resume(candidate_id: str, file: UploadFile = File(...)):
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_RESUME_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOC, or DOCX resumes are accepted.",
        )

    contents = file.file.read()
    if len(contents) > MAX_RESUME_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Resume file is too large (max 10MB).")

    safe_filename = f"{candidate_id}{ext}"
    file_path = RESUME_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(contents)

    candidate = CANDIDATES[candidate_id]
    candidate["resume_filename"] = safe_filename
    candidate["resume_original_name"] = file.filename
    CANDIDATES[candidate_id] = candidate

    return {
        "message": "Resume uploaded",
        "candidate_id": candidate_id,
        "resume_filename": safe_filename,
    }


@router.get("/{candidate_id}/resume")
def download_resume(candidate_id: str, _recruiter: dict = Depends(get_current_recruiter)):
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    filename = candidate.get("resume_filename")

    if not filename:
        raise HTTPException(status_code=404, detail="No resume uploaded for this candidate")

    file_path = RESUME_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Resume file missing on disk")

    original_name = candidate.get("resume_original_name") or filename
    return FileResponse(path=file_path, filename=original_name)


@router.delete("/{candidate_id}")
def delete_candidate(candidate_id: str, _recruiter: dict = Depends(get_current_recruiter)):
    """Fully removes a candidate - their record, assessment, resume
    file, and any recorded audio/video files. Intended for clearing out
    test data before a real demo/presentation, not for production use
    (a real ATS would archive, not hard-delete)."""
    from app.store import ASSESSMENTS
    import shutil

    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]

    resume_filename = candidate.get("resume_filename")
    if resume_filename:
        resume_path = RESUME_DIR / resume_filename
        if resume_path.exists():
            resume_path.unlink()

    recording_dir = RESUME_DIR.parent / "uploaded_recordings" / candidate_id
    if recording_dir.exists():
        shutil.rmtree(recording_dir)

    del CANDIDATES[candidate_id]
    if candidate_id in ASSESSMENTS:
        del ASSESSMENTS[candidate_id]

    return {"message": "Candidate deleted", "candidate_id": candidate_id}
