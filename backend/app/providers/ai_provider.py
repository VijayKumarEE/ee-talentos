"""
AI scoring provider abstraction.

Both providers answer the same question: "given these questions,
reference answers, and the candidate's transcripts, produce a score,
evidence, and summary per competency." The actual grading RULES
(score -> level mapping, overall recommendation thresholds, the
rule-based fallback scorer) live in assessment_service.py and never
change based on provider - only *how the LLM judgment is obtained*
differs here.

LocalAIProvider (Ollama): one call per competency - unchanged from the
original implementation. Free, so there's no reason to batch it.

CloudAIProvider (OpenRouter): ONE combined call covering every
competency in the assessment (see COST CONTROL in the handover brief -
3 separate paid calls per candidate would be 3x the cost for no real
quality gain here, since each competency's grading is independent and
short). Requests structured JSON, validates it before use, and never
raises past this module - any failure (timeout, malformed JSON, budget
ceiling reached) results in `None` for every competency, which the
caller (assessment_service.py) treats exactly like an Ollama failure:
fall back to the deterministic rule-based scorer. A candidate's
assessment is never blocked or duplicated because of this.
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

import httpx

from app.config import (
    APP_MODE,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_ASSESSMENT_MODEL,
)
from app.question_bank import get_reference_for_specific_question
from app.cost_guard import check_budget_or_raise, log_usage, BudgetExceeded

OPENROUTER_TIMEOUT_SECONDS = 45


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
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


class AIProvider(ABC):
    @abstractmethod
    def score_all(
        self,
        competency_defs: List[Any],
        answers: Dict[str, str],
        role_label: str,
        role_slug: str,
        candidate_id: str,
    ) -> Dict[str, Optional[dict]]:
        """Returns {competency_key: {"score", "positive", "gaps",
        "summary"} or None}. A None value means "could not score this
        competency with the LLM" - caller falls back to rule-based
        scoring for that competency only (or all, in the cloud
        provider's case, since one call covers all of them)."""
        raise NotImplementedError


def _consulting_prompt(prompt_text: str, answer: str, role_label: str) -> str:
    return f"""You are an interviewer assessing a candidate's communication skills based on a behavioral/consulting question, for a {role_label} role.

This is NOT a technical question. There is no "correct" answer to grade against. Judge the answer purely on:
- Whether the candidate gives a real, specific example (a real situation, what they actually did, what happened) rather than a vague generality or a hypothetical/textbook answer
- Clarity of communication - is the answer easy to follow, well-structured, and specific rather than rambling or evasive
- Whether they actually answered the question that was asked, rather than talking around it

Question asked: {prompt_text}

Candidate's answer:
\"\"\"{answer if answer else "(no answer provided)"}\"\"\"

Score the candidate's answer from 0 to 5 based on communication quality and specificity of example - NOT technical correctness, since there is none to assess here.

Respond with ONLY a single JSON object, no markdown formatting, no code fences, no extra text, in exactly this shape:
{{"score": <number 0-5>, "positive": ["<short evidence point>"], "gaps": ["<short gap point>"], "summary": "<one sentence>"}}
"""


def _technical_prompt(comp_label: str, comp_prompt: str, reference: str, answer: str, role_label: str) -> str:
    return f"""You are an interviewer scoring a candidate's answer for a {role_label} role.

Competency being assessed: {comp_label}
What this competency covers: {comp_prompt}

Reference knowledge (the "expert answer key" - use this to judge accuracy, do not just check for keyword overlap):
{reference if reference else "No specific reference material - judge on general engineering soundness."}

Candidate's answer:
\"\"\"{answer if answer else "(no answer provided)"}\"\"\"

Score the candidate's answer from 0 to 5 based on how well it demonstrates real understanding of the correct mechanics, not just mentioning the right buzzwords.

Respond with ONLY a single JSON object, no markdown formatting, no code fences, no extra text, in exactly this shape:
{{"score": <number 0-5>, "positive": ["<short evidence point>"], "gaps": ["<short gap point>"], "summary": "<one sentence>"}}
"""


class LocalAIProvider(AIProvider):
    """Unchanged behavior: one Ollama call per competency."""

    def score_all(self, competency_defs, answers, role_label, role_slug, candidate_id):
        from app.services.ollama_service import generate_with_ollama

        results: Dict[str, Optional[dict]] = {}

        for comp_def in competency_defs:
            answer = (answers.get(comp_def.key.value, "") or "").strip()

            if comp_def.key.value == "consulting":
                prompt = _consulting_prompt(comp_def.prompt, answer, role_label)
            else:
                reference = get_reference_for_specific_question(role_slug, comp_def.key.value, candidate_id)
                prompt = _technical_prompt(comp_def.label, comp_def.prompt, reference, answer, role_label)

            try:
                raw = generate_with_ollama(prompt, timeout=25)
                parsed = _extract_json(raw)
                results[comp_def.key.value] = parsed if parsed and "score" in parsed else None
            except Exception:
                results[comp_def.key.value] = None

        return results


class CloudAIProvider(AIProvider):
    """OpenRouter, ONE combined call for every competency in the
    assessment - see module docstring for why. Structured JSON output,
    validated before use."""

    def score_all(self, competency_defs, answers, role_label, role_slug, candidate_id):
        empty: Dict[str, Optional[dict]] = {c.key.value: None for c in competency_defs}

        if not OPENROUTER_API_KEY:
            print("[ai_provider] OPENROUTER_API_KEY not set - cannot score in cloud mode.")
            return empty

        try:
            check_budget_or_raise("assessment")
        except BudgetExceeded as exc:
            print(f"[ai_provider] {exc}")
            return empty

        sections = []
        for comp_def in competency_defs:
            answer = (answers.get(comp_def.key.value, "") or "").strip()
            if comp_def.key.value == "consulting":
                sections.append(
                    f"""Competency key: "consulting"
This is a behavioral/consulting question - there is NO technical reference answer. Judge only communication quality and specificity of a real example.
Question asked: {comp_def.prompt}
Candidate's answer: \"\"\"{answer if answer else '(no answer provided)'}\"\"\""""
                )
            else:
                reference = get_reference_for_specific_question(role_slug, comp_def.key.value, candidate_id)
                sections.append(
                    f"""Competency key: "{comp_def.key.value}" ({comp_def.label})
What this competency covers: {comp_def.prompt}
Reference knowledge (the "expert answer key" - judge accuracy against this, not keyword overlap): {reference if reference else 'No specific reference material - judge on general engineering soundness.'}
Candidate's answer: \"\"\"{answer if answer else '(no answer provided)'}\"\"\""""
                )

        joined_sections = "\n\n---\n\n".join(sections)
        keys = [c.key.value for c in competency_defs]

        prompt = f"""You are an interviewer scoring a candidate's recorded answers for a {role_label} role, one section per competency below.

{joined_sections}

For EACH competency, score 0-5 based on how well the answer demonstrates real understanding (or, for "consulting", real communication/specificity) - not just buzzwords.

Respond with ONLY a single JSON object, no markdown, no code fences, no extra text, in exactly this shape:
{{"results": {{{", ".join(f'"{k}": {{"score": <0-5>, "positive": ["..."], "gaps": ["..."], "summary": "..."}}' for k in keys)}}}}}
"""

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
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
                timeout=OPENROUTER_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            parsed = _extract_json(content)

            usage = data.get("usage", {}) or {}
            cost = usage.get("cost") or usage.get("total_cost")
            log_usage(
                "assessment",
                candidate_id=candidate_id,
                model=OPENROUTER_ASSESSMENT_MODEL,
                cost_usd=float(cost) if cost is not None else None,
                success=bool(parsed),
            )

            if not parsed or "results" not in parsed or not isinstance(parsed["results"], dict):
                print("[ai_provider] OpenRouter returned malformed JSON - falling back to rule-based scoring.")
                return empty

            results = {}
            for key in keys:
                entry = parsed["results"].get(key)
                if entry and "score" in entry:
                    results[key] = entry
                else:
                    results[key] = None
            return results

        except Exception as exc:
            print(f"[ai_provider] OpenRouter assessment call failed: {exc}")
            log_usage("assessment", candidate_id=candidate_id, model=OPENROUTER_ASSESSMENT_MODEL, success=False)
            return empty


def get_ai_provider() -> AIProvider:
    return CloudAIProvider() if APP_MODE == "cloud" else LocalAIProvider()
