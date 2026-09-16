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
