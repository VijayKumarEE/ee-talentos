"""
Local, free speech-to-text using faster-whisper (open-source Whisper
implementation) - runs entirely on this machine, no API key, no
per-use cost, works offline after the one-time model download.

Video recordings have their audio track extracted with ffmpeg first
(Whisper only needs audio, not video pixels), then transcribed the
same way as a direct audio recording.

The model loads lazily on first use (not at server startup) so it
doesn't slow down every backend restart during development - the
first real transcription call will be slower while the model downloads
and loads into memory; every call after that is fast.
"""

import subprocess
from pathlib import Path
from typing import Optional

_model = None

# "base" is a good MVP balance of speed vs accuracy on CPU. Swap to
# "small" or "medium" later for better accuracy at the cost of speed,
# or "tiny" for max speed at the cost of accuracy - same interface.
MODEL_SIZE = "base"


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        print(f"[transcription] Loading Whisper '{MODEL_SIZE}' model (first use only - this downloads once, then is cached locally)...")
        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        print("[transcription] Model ready.")
    return _model


def _extract_audio_from_video(video_path: Path) -> Optional[Path]:
    """Pulls just the audio track out of a video/webm file into a WAV
    file, using ffmpeg. Returns None if ffmpeg isn't available or the
    extraction fails, so callers can fall back gracefully."""
    audio_path = video_path.with_suffix(".extracted.wav")

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vn",  # no video
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        return audio_path
    except FileNotFoundError:
        print("[transcription] ffmpeg not found on this machine - install it with 'brew install ffmpeg' to transcribe video recordings.")
        return None
    except Exception as e:
        print(f"[transcription] Failed to extract audio from video: {e}")
        return None


def transcribe_recording(file_path: Path, mode: str) -> str:
    """Transcribes a saved recording file to text. Returns an empty
    string on any failure (missing ffmpeg, corrupt file, model not
    available, etc.) rather than raising - a failed transcription
    should never block the candidate's flow or crash the upload."""
    audio_path = file_path
    temp_audio_to_clean: Optional[Path] = None

    try:
        if mode == "video":
            extracted = _extract_audio_from_video(file_path)
            if extracted is None:
                return ""
            audio_path = extracted
            temp_audio_to_clean = extracted

        model = _get_model()
        segments, _info = model.transcribe(str(audio_path), beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()
    except Exception as e:
        print(f"[transcription] Failed to transcribe {file_path}: {e}")
        return ""
    finally:
        if temp_audio_to_clean and temp_audio_to_clean.exists():
            temp_audio_to_clean.unlink()