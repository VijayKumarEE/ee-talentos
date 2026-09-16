"""
File storage provider abstraction: resumes and candidate recordings.

LocalStorageProvider: unchanged behavior - files saved under
backend/uploaded_resumes/ and backend/uploaded_recordings/, served
back directly via FastAPI's FileResponse (already protected by
get_current_recruiter for recruiter-only download routes).

CloudStorageProvider: uploads to Supabase Storage over its REST API
(no supabase-py dependency needed - it's a small, stable HTTP API, and
avoiding the extra SDK keeps this a "smallest safe set of changes").
Buckets are PRIVATE by default (never public) - recruiter access goes
through short-lived signed URLs generated on demand, so a resume/
recording is never reachable just because the frontend happens to be
hosted on GitHub Pages. Candidates never receive a signed URL for
another candidate's file; only recruiter-authenticated routes ever
call get_signed_url().

Suggested bucket layout (see HANDOVER addendum for the exact Supabase
setup steps):
    resumes/{candidate_id}{ext}
    recordings/{candidate_id}/{question_id}.webm
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import httpx

from app.config import (
    APP_MODE,
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_RESUME_BUCKET,
    SUPABASE_RECORDING_BUCKET,
    SUPABASE_SIGNED_URL_TTL_SECONDS,
)

RESUME_DIR = Path(__file__).resolve().parent.parent.parent / "uploaded_resumes"
RECORDING_DIR = Path(__file__).resolve().parent.parent.parent / "uploaded_recordings"
RESUME_DIR.mkdir(exist_ok=True)
RECORDING_DIR.mkdir(exist_ok=True)


class StorageProvider(ABC):
    @abstractmethod
    def save_resume(self, candidate_id: str, ext: str, contents: bytes) -> str:
        """Saves the resume, returns a storage reference (LOCAL: a
        filename; CLOUD: a Supabase Storage object path) to persist on
        the candidate record."""
        raise NotImplementedError

    @abstractmethod
    def get_resume_path_or_url(self, storage_ref: str) -> str:
        """Returns something the caller can hand to the client: LOCAL
        returns a local filesystem Path (as str) for FileResponse;
        CLOUD returns a short-lived signed URL to redirect to."""
        raise NotImplementedError

    @abstractmethod
    def save_recording(self, candidate_id: str, question_id: str, contents: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_recording_path_or_url(self, storage_ref: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def local_temp_copy(self, storage_ref: str, bucket: str) -> Path:
        """Returns a local filesystem Path containing the file's bytes,
        downloading it first if needed. Used by transcription (which
        needs a real file on disk for ffmpeg/faster-whisper/OpenRouter
        upload) regardless of where the file is durably stored."""
        raise NotImplementedError


class LocalStorageProvider(StorageProvider):
    def save_resume(self, candidate_id: str, ext: str, contents: bytes) -> str:
        filename = f"{candidate_id}{ext}"
        (RESUME_DIR / filename).write_bytes(contents)
        return filename

    def get_resume_path_or_url(self, storage_ref: str) -> str:
        return str(RESUME_DIR / storage_ref)

    def save_recording(self, candidate_id: str, question_id: str, contents: bytes) -> str:
        candidate_dir = RECORDING_DIR / candidate_id
        candidate_dir.mkdir(exist_ok=True)
        filename = f"{question_id}.webm"
        (candidate_dir / filename).write_bytes(contents)
        return f"{candidate_id}/{filename}"

    def get_recording_path_or_url(self, storage_ref: str) -> str:
        return str(RECORDING_DIR / storage_ref)

    def local_temp_copy(self, storage_ref: str, bucket: str) -> Path:
        base = RESUME_DIR if bucket == "resumes" else RECORDING_DIR
        return base / storage_ref


class CloudStorageProvider(StorageProvider):
    """Talks directly to Supabase Storage's REST API using the
    service-role key. This key lives ONLY on the backend (an env var
    read here, in app/config.py) and is never sent to the browser."""

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"}

    def _upload(self, bucket: str, object_path: str, contents: bytes) -> None:
        url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{object_path}"
        resp = httpx.post(
            url,
            headers={**self._headers(), "x-upsert": "true"},
            content=contents,
            timeout=60,
        )
        resp.raise_for_status()

    def _download(self, bucket: str, object_path: str) -> bytes:
        url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{object_path}"
        resp = httpx.get(url, headers=self._headers(), timeout=60)
        resp.raise_for_status()
        return resp.content

    def _signed_url(self, bucket: str, object_path: str) -> str:
        url = f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{object_path}"
        resp = httpx.post(
            url,
            headers=self._headers(),
            json={"expiresIn": SUPABASE_SIGNED_URL_TTL_SECONDS},
            timeout=15,
        )
        resp.raise_for_status()
        signed_path = resp.json()["signedURL"]
        return f"{SUPABASE_URL}/storage/v1{signed_path}"

    def save_resume(self, candidate_id: str, ext: str, contents: bytes) -> str:
        object_path = f"{candidate_id}{ext}"
        self._upload(SUPABASE_RESUME_BUCKET, object_path, contents)
        return object_path

    def get_resume_path_or_url(self, storage_ref: str) -> str:
        return self._signed_url(SUPABASE_RESUME_BUCKET, storage_ref)

    def save_recording(self, candidate_id: str, question_id: str, contents: bytes) -> str:
        object_path = f"{candidate_id}/{question_id}.webm"
        self._upload(SUPABASE_RECORDING_BUCKET, object_path, contents)
        return object_path

    def get_recording_path_or_url(self, storage_ref: str) -> str:
        return self._signed_url(SUPABASE_RECORDING_BUCKET, storage_ref)

    def local_temp_copy(self, storage_ref: str, bucket: str) -> Path:
        import tempfile

        source_bucket = SUPABASE_RESUME_BUCKET if bucket == "resumes" else SUPABASE_RECORDING_BUCKET
        contents = self._download(source_bucket, storage_ref)

        suffix = Path(storage_ref).suffix or ".bin"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(contents)
        tmp.close()
        return Path(tmp.name)


def get_storage_provider() -> StorageProvider:
    return CloudStorageProvider() if APP_MODE == "cloud" else LocalStorageProvider()
