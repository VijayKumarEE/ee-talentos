"""
Transcription provider abstraction.

LocalTranscriptionProvider: unchanged - thin wrapper around the
existing faster-whisper implementation in services/transcription_service.py.

CloudTranscriptionProvider: sends just the extracted audio (never the
raw video - see COST CONTROL in the handover brief: video adds bytes
and latency for zero transcription benefit) to an OpenRouter model
that accepts audio input, as a base64-encoded data URL in the chat
message content, with a system instruction to return the spoken words
only. Video recordings still have their audio extracted locally first
with ffmpeg (this step needs no cloud service and costs nothing) -
only the resulting short audio clip is sent to OpenRouter.

Both providers implement transcribe(file_path, mode) -> str and never
raise: any failure returns "" so a flaky network/model can never block
a candidate's upload or crash the request, exactly like the original
faster-whisper implementation's contract.
"""

import base64
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import httpx

from app.config import (
    APP_MODE,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_TRANSCRIPTION_MODEL,
)
from app.cost_guard import check_budget_or_raise, log_usage, BudgetExceeded

OPENROUTER_TRANSCRIPTION_TIMEOUT_SECONDS = 60


class TranscriptionProvider(ABC):
    @abstractmethod
    def transcribe(self, file_path: Path, mode: str, candidate_id: str = "") -> str:
        raise NotImplementedError


class LocalTranscriptionProvider(TranscriptionProvider):
    def transcribe(self, file_path: Path, mode: str, candidate_id: str = "") -> str:
        from app.services.transcription_service import transcribe_recording
        return transcribe_recording(file_path, mode)


class CloudTranscriptionProvider(TranscriptionProvider):
    def transcribe(self, file_path: Path, mode: str, candidate_id: str = "") -> str:  # noqa: D401
        from app.services.transcription_service import _extract_audio_from_video

        if not OPENROUTER_API_KEY:
            print("[transcription_provider] OPENROUTER_API_KEY not set - cannot transcribe in cloud mode.")
            return ""

        audio_path = file_path
        temp_audio_to_clean: Optional[Path] = None

        try:
            if mode == "video":
                extracted = _extract_audio_from_video(file_path)
                if extracted is None:
                    return ""
                audio_path = extracted
                temp_audio_to_clean = extracted

            try:
                check_budget_or_raise("transcription")
            except BudgetExceeded as exc:
                print(f"[transcription_provider] {exc}")
                return ""

            audio_bytes = audio_path.read_bytes()
            audio_b64 = base64.b64encode(audio_bytes).decode("ascii")

            resp = httpx.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_TRANSCRIPTION_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Transcribe the spoken words in this audio clip exactly. "
                                        "Respond with ONLY the transcript text, no commentary, "
                                        "no timestamps, no speaker labels."
                                    ),
                                },
                                {
                                    "type": "input_audio",
                                    "input_audio": {"data": audio_b64, "format": "wav"},
                                },
                            ],
                        }
                    ],
                    "temperature": 0.0,
                },
                timeout=OPENROUTER_TRANSCRIPTION_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (data["choices"][0]["message"]["content"] or "").strip()

            usage = data.get("usage", {}) or {}
            cost = usage.get("cost") or usage.get("total_cost")
            log_usage(
                "transcription",
                candidate_id=candidate_id,
                model=OPENROUTER_TRANSCRIPTION_MODEL,
                cost_usd=float(cost) if cost is not None else None,
                success=bool(text),
            )

            return text
        except Exception as exc:
            print(f"[transcription_provider] OpenRouter transcription failed for {file_path}: {exc}")
            log_usage("transcription", candidate_id=candidate_id, model=OPENROUTER_TRANSCRIPTION_MODEL, success=False)
            return ""
        finally:
            if temp_audio_to_clean and temp_audio_to_clean.exists():
                temp_audio_to_clean.unlink()


def get_transcription_provider() -> TranscriptionProvider:
    return CloudTranscriptionProvider() if APP_MODE == "cloud" else LocalTranscriptionProvider()
