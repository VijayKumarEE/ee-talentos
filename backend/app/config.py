"""
Central config for the scheduling / email features.

Everything here is a placeholder for the buildathon MVP:
- EMAIL_MODE="console" just prints emails to the backend terminal instead
  of sending real ones. Swap to "smtp" later once you wire up real email.
- Slot generation is mocked (see services/scheduling_service.py) instead
  of calling the real Google Calendar API.

Nothing here needs real secrets yet, so it's safe to commit as-is.
"""

EMAIL_MODE = "console"  # "console" | "smtp" (smtp not implemented yet)

EMAIL_FROM = "noreply@prescreen-mvp.local"

RECRUITER_EMAIL = "recruiter@company.local"
PANEL_EMAILS = ["panel1@company.local", "panel2@company.local"]

# Mock scheduling window: how many business days ahead to offer slots,
# and how many slots per day.
SCHEDULING_DAYS_AHEAD = 5
SLOTS_PER_DAY = 3
SLOT_DURATION_MINUTES = 45
BUSINESS_START_HOUR = 10  # 10 AM

# --- GitHub showcase (github_showcase_service.py) ---
# Loaded from backend/.env (see .env.example) so the token never sits in
# source code. If any of these are missing, the showcase push is simply
# skipped - it never blocks a candidate applying or a recruiter scoring.
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GITHUB_DATA_PATH = os.getenv("GITHUB_DATA_PATH", "data/candidates.json")

# --- APP_MODE: the one switch that decides everything below --------
# "local"  -> SQLite + Ollama + faster-whisper + local filesystem (default,
#             unchanged behavior, no internet/API keys required).
# "cloud"  -> Supabase Postgres + OpenRouter (AI + transcription) +
#             Supabase Storage. See app/providers/ for the actual
#             implementations picked based on this flag.
APP_MODE = os.getenv("APP_MODE", "local").strip().lower()
IS_CLOUD_MODE = APP_MODE == "cloud"

# --- Cloud database (Supabase Postgres) ------------------------------
# A direct Postgres connection string (Supabase Settings -> Database ->
# Connection string -> "Transaction" pooler recommended for
# serverless/free-tier hosts like Render). Only used when APP_MODE=cloud.
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")

# --- Supabase project (for Storage + optional Supabase Auth) ---------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
# Service-role key: full-access, backend-only. NEVER send this to the
# frontend/browser under any circumstance.
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

SUPABASE_RESUME_BUCKET = os.getenv("SUPABASE_RESUME_BUCKET", "resumes")
SUPABASE_RECORDING_BUCKET = os.getenv("SUPABASE_RECORDING_BUCKET", "recordings")
# How long a recruiter's signed download link stays valid.
SUPABASE_SIGNED_URL_TTL_SECONDS = int(os.getenv("SUPABASE_SIGNED_URL_TTL_SECONDS", "3600"))

# --- OpenRouter (cloud AI + cloud transcription) ---------------------
# Never exposed to the browser - only read on the backend.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Cheap-but-capable model for structured candidate-answer scoring.
# google/gemini-2.5-flash is a good cost/quality default; override freely.
OPENROUTER_ASSESSMENT_MODEL = os.getenv("OPENROUTER_ASSESSMENT_MODEL", "google/gemini-2.5-flash")

# Model used for cloud speech-to-text. Any OpenRouter model that accepts
# audio input works here (see providers/transcription_provider.py for
# how it's called). Defaults to a small multimodal model suitable for
# short candidate answers.
OPENROUTER_TRANSCRIPTION_MODEL = os.getenv("OPENROUTER_TRANSCRIPTION_MODEL", "google/gemini-2.5-flash")

# --- Cost controls (see app/cost_guard.py) ---------------------------
# A soft monthly ceiling in USD. This is enforced approximately, from
# the usage OpenRouter reports back per call (when available) - it is
# NOT a substitute for setting a real spend cap in the OpenRouter
# dashboard, which you should also do.
AI_MONTHLY_BUDGET_USD = float(os.getenv("AI_MONTHLY_BUDGET_USD", "20"))
# Hard ceiling on the number of assessment-scoring calls per calendar
# month, regardless of reported cost - a safety net if usage reporting
# is ever missing/wrong.
AI_MAX_ASSESSMENT_CALLS_PER_MONTH = int(os.getenv("AI_MAX_ASSESSMENT_CALLS_PER_MONTH", "500"))

# --- Zoom (interview confirmation email) -----------------------------
# Optional. A single shared meeting room link is enough for a
# buildathon MVP - a real Zoom API integration (auto-creating a unique
# meeting per interview) needs its own Zoom developer app/credentials,
# which is more setup than this needs right now. If left blank, the
# confirmation email just omits the link and says "link to follow."
ZOOM_MEETING_LINK = os.getenv("ZOOM_MEETING_LINK", "")

# --- CORS -------------------------------------------------------------
# Comma-separated list of allowed origins for CLOUD MODE (e.g. your
# GitHub Pages origin: "https://yourname.github.io"). LOCAL MODE keeps
# its own hard-coded localhost list in main.py regardless of this.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
