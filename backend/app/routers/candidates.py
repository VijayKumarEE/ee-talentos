import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request, Body
from fastapi.responses import FileResponse, RedirectResponse

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
from app.providers.storage_provider import get_storage_provider
from app.config import IS_CLOUD_MODE

router = APIRouter(prefix="/candidates", tags=["candidates"])

# LOCAL MODE: resumes on disk under backend/uploaded_resumes/.
# CLOUD MODE: resumes in the Supabase "resumes" bucket, private,
# accessed only via short-lived signed URLs (see storage_provider.py).
# Either way, routers only ever go through storage_provider - never
# touch a filesystem path directly - so this switch is invisible here.
storage = get_storage_provider()

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

    storage_ref = storage.save_resume(candidate_id, ext, contents)

    candidate = CANDIDATES[candidate_id]
    candidate["resume_filename"] = storage_ref
    candidate["resume_original_name"] = file.filename
    CANDIDATES[candidate_id] = candidate

    return {
        "message": "Resume uploaded",
        "candidate_id": candidate_id,
        "resume_filename": storage_ref,
    }


@router.get("/{candidate_id}/resume")
def download_resume(candidate_id: str, _recruiter: dict = Depends(get_current_recruiter)):
    """LOCAL MODE serves the file directly. CLOUD MODE redirects to a
    short-lived Supabase signed URL - the resume itself is never public,
    and this route is still behind get_current_recruiter, so a
    candidate can never mint their own signed URL for anyone's resume,
    only a logged-in recruiter can reach this route at all."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    storage_ref = candidate.get("resume_filename")

    if not storage_ref:
        raise HTTPException(status_code=404, detail="No resume uploaded for this candidate")

    if IS_CLOUD_MODE:
        try:
            signed_url = storage.get_resume_path_or_url(storage_ref)
        except Exception:
            raise HTTPException(status_code=404, detail="Resume file missing in storage")
        return RedirectResponse(url=signed_url)

    file_path = Path(storage.get_resume_path_or_url(storage_ref))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Resume file missing on disk")

    original_name = candidate.get("resume_original_name") or storage_ref
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

    # Best-effort file cleanup. LOCAL MODE deletes from disk directly;
    # CLOUD MODE is intentionally not deleted from Supabase Storage here
    # (buildathon MVP scope - see HANDOVER addendum) - the database
    # record is removed either way, which is what the dashboard/API
    # actually reads.
    if not IS_CLOUD_MODE:
        from app.providers.storage_provider import RESUME_DIR, RECORDING_DIR

        resume_filename = candidate.get("resume_filename")
        if resume_filename:
            resume_path = RESUME_DIR / resume_filename
            if resume_path.exists():
                resume_path.unlink()

        recording_dir = RECORDING_DIR / candidate_id
        if recording_dir.exists():
            shutil.rmtree(recording_dir)

    del CANDIDATES[candidate_id]
    if candidate_id in ASSESSMENTS:
        del ASSESSMENTS[candidate_id]

    return {"message": "Candidate deleted", "candidate_id": candidate_id}


@router.post("/{candidate_id}/availability")
def submit_availability(
    candidate_id: str,
    slots: list[str] = Body(default=[]),
    notes: str = Body(default=""),
):
    """Candidate states their own availability right after finishing
    the assessment - not picking from a recruiter's pre-set slots
    (that's the separate, existing SchedulingPage/booking flow, still
    intact and untouched). This is the other direction: the candidate
    tells the recruiter when THEY'RE free, in their own words/picks, so
    the recruiter can see it on the Shortlist page and confirm a real
    time directly (see /scheduling/{candidate_id}/confirm-interview),
    without an email back-and-forth to find a slot.

    `slots` are simple human-readable strings the frontend builds from
    a lightweight day/time-window picker (e.g. "Thu 18 Sep, Morning
    (10am-12pm)") - deliberately not a rigid structured format, since
    candidates also need `notes` for anything ad hoc that doesn't fit
    a preset window (e.g. "any day after 6pm IST")."""
    if candidate_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = CANDIDATES[candidate_id]
    candidate["candidate_availability"] = {
        "slots": slots,
        "notes": notes.strip(),
    }
    CANDIDATES[candidate_id] = candidate

    return {"message": "Availability saved", "candidate_id": candidate_id}
