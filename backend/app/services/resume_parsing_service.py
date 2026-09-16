"""
Resume parsing for the "upload first, auto-fill the rest" flow.

Pipeline:
1. extract_resume_text() pulls raw text out of a PDF or DOCX file.
   Legacy .doc (old binary Word format) isn't supported by any
   lightweight pure-Python library, so it's deliberately not attempted -
   returns empty text, and the caller falls back to manual entry rather
   than erroring out.
2. Email, phone, and full name are extracted with plain pattern-matching
   and simple heuristics - NOT the AI. These follow predictable enough
   patterns (an email always has an @ and a domain; a name is almost
   always the first real line of text) that asking a small local model
   to find them is both unnecessary and less reliable than just
   pattern-matching directly.
3. Only current_location and current_organization - which genuinely
   require understanding context ("which job is the current one?",
   "is this a home address or a client site mentioned later?") - are
   sent to Ollama. Asking a small model for 2 things it's suited to
   reason about is far more reliable than asking it for 5 things at
   once, some of which don't need reasoning at all.

Every step fails safely: a corrupt file, an unsupported format, or an
unavailable Ollama should never block the candidate from continuing -
whatever isn't found is just left blank for manual entry, exactly as
before this feature existed.
"""

import io
import json
import re
from typing import Optional

from app.services.ollama_service import generate_with_ollama

RESUME_PARSE_TIMEOUT_SECONDS = 60

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Matches a run of digits with common separators mixed in (spaces,
# dots, dashes, parens) - deliberately NOT tied to a specific grouping
# like 3-3-4 (US-style), since that rigid shape mathematically cannot
# match the equally common Indian mobile format "+91 90000 00000"
# (a 5+5 split). Validity is decided afterward by total digit count,
# not by which positions the separators fall in.
_PHONE_CANDIDATE_PATTERN = re.compile(r"\+?\d[\d\s().-]{5,18}\d")


def extract_resume_text(file_bytes: bytes, filename: str) -> str:
    lower_name = (filename or "").lower()

    try:
        if lower_name.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n".join((page.extract_text() or "") for page in reader.pages)

        if lower_name.endswith(".docx"):
            from docx import Document

            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)

        # .doc (legacy binary Word format) - no reliable lightweight
        # extraction available, so we don't attempt it.
        return ""
    except Exception:
        # Any parsing failure (corrupt file, unexpected format
        # variant, etc.) - never raise, just return nothing so the
        # candidate falls back to manual entry.
        return ""


def _extract_email(text: str) -> Optional[str]:
    match = _EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> Optional[str]:
    # Search only the first 500 characters (contact info is always
    # near the top) to avoid accidentally matching a random number
    # embedded later in the document (dates, certification IDs, etc.)
    window = text[:500]
    for match in _PHONE_CANDIDATE_PATTERN.finditer(window):
        candidate = match.group(0).strip()

        # Reject currency-shaped matches (e.g. a salary figure like
        # "175,000.00" bleeding into the window) - a real phone number
        # essentially never ends a group in exactly two decimal places.
        if re.search(r"\.\d{2}\b", candidate):
            continue

        digit_count = sum(c.isdigit() for c in candidate)
        # A real phone number (with country code) is 7-15 digits.
        # Below 7 filters out short accidental matches (a year, a page
        # number); above 15 filters out things like a long ID number
        # that happens to be all digits.
        if 7 <= digit_count <= 15:
            return candidate
    return None


_MONTH_NAMES = {
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}


def _looks_like_date_line(line: str) -> bool:
    """Detects lines like 'March 2024 - Current' or a bare year like
    '2024'. Some resumes use a sidebar/timeline layout where the
    extracted text pulls date ranges out BEFORE the name itself -
    without this check, those dates would be mistaken for (or block
    us from ever reaching) the actual name."""
    lower = line.lower()
    words = re.findall(r"[a-zA-Z]+", lower)
    has_month = any(w in _MONTH_NAMES for w in words)
    has_year = bool(re.search(r"\b(19|20)\d{2}\b", line))

    if has_month and has_year:
        return True
    if re.fullmatch(r"(19|20)\d{2}", line.strip()):
        return True
    return False


def _name_candidate_from_line(line: str) -> Optional[str]:
    """Trims a line down to just the leading name-like portion (in
    case contact info is merged onto the same line with no line
    break), and returns it only if what's left plausibly looks like a
    name - short, no digits, no email/pipe characters."""
    cutoff = len(line)
    for marker in ("|", "@"):
        idx = line.find(marker)
        if idx != -1:
            cutoff = min(cutoff, idx)

    digit_run = re.search(r"\d{3,}", line[:cutoff])
    if digit_run:
        cutoff = min(cutoff, digit_run.start())

    candidate = line[:cutoff].strip().rstrip(",:;-").strip()

    if not candidate:
        return None

    word_count = len(candidate.split())
    if 1 <= word_count <= 5 and len(candidate) <= 60 and not any(c.isdigit() for c in candidate):
        return candidate
    return None


def _extract_name(text: str) -> Optional[str]:
    """Scans the first several non-empty lines (not just the very
    first one) looking for the candidate's name. Two things resumes
    genuinely do that a naive "just take line 1" approach breaks on:

    1. A sidebar/timeline layout can cause date ranges ("March 2024 -
       Current") to be extracted BEFORE the name at all - these are
       skipped rather than mistaken for a name or treated as a
       dead end.
    2. Some layouts split the name across two separate lines (e.g.
       "ANAND" then "PRAKASH" right after it) - if a single-word
       candidate is immediately followed by another plausible
       single-word candidate in the same casing style, they're joined
       into one name.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    max_lines_to_scan = 10

    for idx, line in enumerate(lines[:max_lines_to_scan]):
        if _looks_like_date_line(line):
            continue

        candidate = _name_candidate_from_line(line)
        if not candidate:
            continue

        if len(candidate.split()) == 1 and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            if not _looks_like_date_line(next_line):
                next_candidate = _name_candidate_from_line(next_line)
                if (
                    next_candidate
                    and len(next_candidate.split()) == 1
                    and len(next_candidate) <= 30
                    and next_candidate.isupper() == candidate.isupper()
                ):
                    return f"{candidate} {next_candidate}"

        return candidate

    return None


def _extract_json(text: str) -> Optional[dict]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _extract_location_org_and_title_via_ai(resume_text: str) -> dict:
    """current_location, current_organization, and current_title all go
    through the AI - these need contextual understanding, not the
    pattern-matching used for name/email/phone. current_title is asked
    alongside current_organization deliberately - both are about the
    exact same "most recent job entry", so it's one small addition to
    a question the model is already answering, not a separate call."""
    empty = {"current_location": None, "current_organization": None, "current_title": None}

    truncated_text = resume_text[:4000]

    prompt = f"""Extract these 3 fields from the resume text below:

- current_location: the city/area the person lives in (often written like "Katraj, Pune" near the top). NOT a client site or project location mentioned later in the resume.
- current_organization: the employer in the MOST RECENT work experience entry - look for the job whose date range says "Present", "Current", or has no end date. It is NOT the candidate's job title, and NOT a client name mentioned inside a project description (e.g. if the resume says "Project Name: BMW FLAT" under an employer called "HCL Technologies", the current_organization is "HCL Technologies", not "BMW FLAT").
- current_title: the candidate's job title/position in that SAME most recent entry (e.g. "DevOps Engineer", "Senior Software Developer") - often labeled "Position:" or written right after the employer name.

The resume may contain a skills table where multiple unrelated skill categories run together as one block of text (e.g. "Front End HTML CSS Database PostgreSQL Back End C#") - ignore that section entirely, it never contains location, employer, or title information.

If a field genuinely isn't in the text, use null - do not guess.

Resume text:
\"\"\"{truncated_text}\"\"\"

Respond with ONLY a single JSON object, no markdown, no extra text, in exactly this shape:
{{"current_location": "<value or null>", "current_organization": "<value or null>", "current_title": "<value or null>"}}
"""

    try:
        raw = generate_with_ollama(prompt, timeout=RESUME_PARSE_TIMEOUT_SECONDS)
        parsed = _extract_json(raw)

        if not parsed:
            return empty

        return {
            "current_location": parsed.get("current_location") or None,
            "current_organization": parsed.get("current_organization") or None,
            "current_title": parsed.get("current_title") or None,
        }
    except Exception:
        return empty


def extract_candidate_fields(resume_text: str) -> dict:
    """Returns whatever subset of {full_name, phone, email,
    current_location, current_organization, current_title} could be
    confidently identified in the resume text. email/phone/full_name
    are found via reliable pattern-matching (no AI, no timeout risk,
    no JSON-parsing risk). current_location/current_organization/
    current_title go through the AI since they need contextual
    understanding. Any field not found is simply omitted (never
    guessed), so the candidate fills it in themselves rather than
    seeing a wrong auto-filled value."""
    empty_result = {
        "full_name": None,
        "phone": None,
        "email": None,
        "current_location": None,
        "current_organization": None,
        "current_title": None,
    }

    if not resume_text or not resume_text.strip():
        return empty_result

    result = dict(empty_result)
    result["full_name"] = _extract_name(resume_text)
    result["email"] = _extract_email(resume_text)
    result["phone"] = _extract_phone(resume_text)

    ai_fields = _extract_location_org_and_title_via_ai(resume_text)
    result["current_location"] = ai_fields["current_location"]
    result["current_organization"] = ai_fields["current_organization"]
    result["current_title"] = ai_fields["current_title"]

    return result