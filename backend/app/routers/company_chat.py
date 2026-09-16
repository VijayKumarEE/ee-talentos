"""
Candidate-facing "ask about Equal Experts" chatbot for the /apply page.

Deliberately NOT a free-form chat. The LLM's only job is to classify
the candidate's typed message into one of a small, fixed set of
topics (and, for JD questions, which of the 10 roles they mean). The
actual text shown to the candidate always comes from company_info.py -
pre-written, pre-approved content - never something the model
generates on the fly. This means the model can't be steered into
inventing facts, going off-topic, or - importantly - discussing
anything about the assessment questions, scoring, or other candidates,
since "fallback" is the only thing it can return for anything outside
the fixed topic list.

Rate-limited (not auth-gated, since candidates never log in) because
this is a public, unauthenticated endpoint that costs an LLM call per
message - the same lightweight in-memory limiter already used for
/auth/login.
"""

import json
import random
import re
from typing import Optional

from fastapi import APIRouter, Body, Request

from app.company_info import (
    COMPANY_OVERVIEW,
    COMPANY_OVERVIEW_ICON,
    LINKEDIN_URL,
    GLASSDOOR_URL,
    GLASSDOOR_BLURB,
    GLASSDOOR_ICON,
    GLASSDOOR_STAT,
    GLASSDOOR_CAPTION,
    VALUES,
    VALUES_ICON,
    INTERVIEW_PROCESS,
    NETWORK_BENEFITS,
    NETWORK_BENEFITS_ICON,
    CAREERS_PAGE_URL,
    ROLE_JD_LINKS,
    FUN_FACTS,
    LIFE_AT_EE_URL,
    TEAM_URL,
    CASE_STUDIES_URL,
    CONTACT_EMAIL,
)
from app.roles import ROLES
from app.rate_limiter import check_rate_limit
from app.config import APP_MODE, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_ASSESSMENT_MODEL
from app.services.ollama_service import generate_with_ollama
from app.cost_guard import check_budget_or_raise, log_usage, BudgetExceeded

router = APIRouter(prefix="/company-chat", tags=["company-chat"])

CHAT_TIMEOUT_SECONDS = 15


def _generate_for_classification(prompt: str) -> str:
    """LOCAL MODE: Ollama, unchanged. CLOUD MODE: OpenRouter. This is a
    classification-only call (topic + optional role, from a small
    fixed list) - short prompt, short response - so it reuses the same
    cheap assessment model rather than needing its own env var.
    Returns "" on any failure so the caller always falls back to
    FALLBACK_REPLY, exactly as it already did against a down/missing
    Ollama."""
    if APP_MODE != "cloud":
        return generate_with_ollama(prompt, timeout=CHAT_TIMEOUT_SECONDS)

    if not OPENROUTER_API_KEY:
        return ""

    try:
        check_budget_or_raise("chat_classification")
    except BudgetExceeded as exc:
        print(f"[company_chat] {exc}")
        return ""

    import httpx

    try:
        resp = httpx.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_ASSESSMENT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=CHAT_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        usage = data.get("usage", {}) or {}
        cost = usage.get("cost") or usage.get("total_cost")
        log_usage(
            "chat_classification",
            model=OPENROUTER_ASSESSMENT_MODEL,
            cost_usd=float(cost) if cost is not None else None,
            success=True,
        )
        return content
    except Exception as exc:
        print(f"[company_chat] OpenRouter classification failed: {exc}")
        log_usage("chat_classification", model=OPENROUTER_ASSESSMENT_MODEL, success=False)
        return ""

FALLBACK_REPLY = (
    "I can help with information about Equal Experts - our LinkedIn page, "
    "Glassdoor reviews, our values, the interview process, network "
    "benefits, or a link to a specific role's job description. What "
    "would you like to know? For anything else, feel free to reach out "
    f"to {CONTACT_EMAIL}."
)

_ROLE_VALUES = [r["value"] for r in ROLES]


def _extract_json(text: str) -> Optional[dict]:
    """Ollama sometimes wraps JSON in markdown fences or adds stray
    text around it. Try direct parse first, then fall back to pulling
    out the first {...} block. (Deliberately duplicated here rather
    than imported from assessment_service.py - that copy is a private
    helper local to that module, and this router shouldn't reach
    across module boundaries for a private symbol.)"""
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


def _classify_message(message: str) -> dict:
    """Asks Ollama to pick one topic from a fixed list, and (for JD
    questions) which role. Returns {"topic": "fallback"} on any
    failure - a broken/unavailable Ollama should degrade to the
    generic help message, never break the widget."""
    role_list = ", ".join(_ROLE_VALUES)

    prompt = f"""You are classifying a candidate's message on a job application page into ONE topic. You are NOT answering the question yourself - only picking a category.

Valid topics: company_overview, linkedin, glassdoor, values, interview_process, network_benefits, life_at_ee, team, case_studies, jd, fallback

Use "jd" if the candidate is asking about a specific role or job description. Use "fallback" for ANYTHING else, including questions about the assessment, scoring, other candidates, salary negotiation, or anything not about Equal Experts as a company.

If the topic is "jd", also pick which role from this exact list it most likely refers to: {role_list}
If it's a JD question but you can't tell which role, use "unclear" for the role.

Candidate's message:
\"\"\"{message}\"\"\"

Respond with ONLY a single JSON object, no markdown, no extra text, in exactly this shape:
{{"topic": "<one of the valid topics above>", "role": "<role value or 'unclear', only if topic is jd, otherwise omit>"}}
"""

    try:
        raw = _generate_for_classification(prompt)
        parsed = _extract_json(raw)

        if not parsed or "topic" not in parsed:
            return {"topic": "fallback"}

        return parsed
    except Exception:
        return {"topic": "fallback"}


def _build_reply(classification: dict) -> dict:
    """Maps a classified topic to the pre-written, pre-approved
    response. This is the ONLY place candidate-visible text gets
    chosen - the model never generates what's actually shown.

    Every reply includes both a plain-text `reply` field (fallback for
    anything that doesn't render the richer display, and for
    accessibility) and an optional `display` object telling the
    frontend how to render it visually:
      - "stat_card": icon + bold headline stat + caption (+ optional link)
      - "icon_list": icon + a list of short items
      - "step_list": a numbered list of items
      - "info_card": icon + a longer paragraph
      - omitted entirely: render as a plain text bubble (unchanged)

    Also always includes the resolved `topic` itself, so the frontend
    can track which topics have already been answered - whether the
    candidate got there by clicking a suggestion chip or by typing
    their own question - and stop suggesting that topic again.
    """
    topic = classification.get("topic")

    if topic == "company_overview":
        return {
            "reply": COMPANY_OVERVIEW,
            "link": None,
            "display": {"type": "info_card", "icon": COMPANY_OVERVIEW_ICON, "caption": COMPANY_OVERVIEW},
            "topic": topic,
        }

    if topic == "linkedin":
        # Deliberately left as a plain bubble, not a card - it's
        # already short and a card would add visual weight for no
        # benefit here.
        return {"reply": "Here's our LinkedIn page:", "link": LINKEDIN_URL, "topic": topic}

    if topic == "glassdoor":
        return {
            "reply": GLASSDOOR_BLURB,
            "link": GLASSDOOR_URL,
            "display": {
                "type": "stat_card",
                "icon": GLASSDOOR_ICON,
                "stat": GLASSDOOR_STAT,
                "caption": GLASSDOOR_CAPTION,
            },
            "topic": topic,
        }

    if topic == "values":
        values_text = "Our values:\n" + "\n".join(f"- {v}" for v in VALUES)
        return {
            "reply": values_text,
            "link": None,
            "display": {"type": "icon_list", "icon": VALUES_ICON, "items": VALUES},
            "topic": topic,
        }

    if topic == "interview_process":
        steps_text = "Our interview process typically involves:\n" + "\n".join(
            f"{i + 1}. {step}" for i, step in enumerate(INTERVIEW_PROCESS)
        )
        return {
            "reply": steps_text,
            "link": None,
            "display": {"type": "step_list", "items": INTERVIEW_PROCESS},
            "topic": topic,
        }

    if topic == "network_benefits":
        benefits_text = "Some benefits of joining the Equal Experts network:\n" + "\n".join(
            f"- {b}" for b in NETWORK_BENEFITS
        )
        return {
            "reply": benefits_text,
            "link": None,
            "display": {"type": "icon_list", "icon": NETWORK_BENEFITS_ICON, "items": NETWORK_BENEFITS},
            "topic": topic,
        }

    if topic == "life_at_ee":
        return {"reply": "Here's a look at life at Equal Experts:", "link": LIFE_AT_EE_URL, "topic": topic}

    if topic == "team":
        return {"reply": "Here's our leadership team:", "link": TEAM_URL, "topic": topic}

    if topic == "case_studies":
        return {"reply": "Here are some of our case studies:", "link": CASE_STUDIES_URL, "topic": topic}

    if topic == "jd":
        role: Optional[str] = classification.get("role")

        if role not in ROLE_JD_LINKS:
            return {
                "reply": (
                    "I'm not sure which role you mean - you can see all our "
                    "current openings here:"
                ),
                "link": CAREERS_PAGE_URL,
                "topic": topic,
            }

        link = ROLE_JD_LINKS[role]

        if link is None:
            return {
                "reply": (
                    "There isn't an active opening for that role posted right "
                    "now, but you can see everything we currently have open here:"
                ),
                "link": CAREERS_PAGE_URL,
                "topic": topic,
            }

        return {"reply": "Here's the job description for that role:", "link": link, "topic": topic}

    return {"reply": FALLBACK_REPLY, "link": None, "topic": "fallback"}


@router.post("/ask")
def ask(request: Request, message: str = Body(..., embed=True)):
    client_ip = request.client.host if request.client else "unknown"
    # Generous but real - this is an unauthenticated public endpoint
    # that costs an LLM call per message, so it gets the same
    # lightweight protection as /auth/login.
    check_rate_limit(f"company-chat:{client_ip}", max_attempts=20, window_seconds=60)

    classification = _classify_message(message)
    return _build_reply(classification)


@router.post("/fun-fact")
def fun_fact(request: Request):
    """Picks one random fact - deliberately not routed through the LLM
    classifier, since there's no ambiguity to resolve. Shares the same
    rate-limit budget as /ask (same client_ip key) since it's a cheap
    call but still an unauthenticated public endpoint."""
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"company-chat:{client_ip}", max_attempts=20, window_seconds=60)

    return random.choice(FUN_FACTS)