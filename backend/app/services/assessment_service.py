import json
import re
from typing import List, Optional, Dict, Any

from app.schemas import (
    CandidateAssessmentRequest,
    CandidateAssessmentResponse,
    CompetencyDefinition,
    CompetencyKey,
    CompetencyScore,
    SkillEvidence,
    Recommendation,
)
from app.question_bank import get_reference_for_role_competency, get_reference_for_specific_question
from app.services.ollama_service import generate_with_ollama

LEVELS = [
    "novice",
    "advanced_beginner",
    "competent",
    "proficient",
    "expert",
]

# Scoring calls get a short timeout so one slow/unavailable Ollama call
# can't stall a live demo - we fall back to rule-based scoring instantly
# if this is exceeded or anything goes wrong.
OLLAMA_SCORING_TIMEOUT_SECONDS = 25


def _score_to_level(score: float) -> str:
    if score < 1.5:
        return "novice"
    if score < 2.5:
        return "advanced_beginner"
    if score < 3.5:
        return "competent"
    if score < 4.5:
        return "proficient"
    return "expert"


def _rule_based_score(answer: str, comp_def: CompetencyDefinition) -> CompetencyScore:
    """Fallback scorer: fast, deterministic, no external dependency.
    Used whenever Ollama scoring fails, times out, or returns something
    unparseable - so a flaky local LLM never breaks the demo."""
    score = 0.0
    evidence = SkillEvidence()

    if answer:
        score += 2.0
        evidence.positive.append(f"Candidate answered the {comp_def.label} question.")
    else:
        evidence.gaps.append(f"No answer provided for {comp_def.label}.")
        evidence.risk_flags.append("No evidence")

    if any(word in answer for word in ["production", "incident", "troubleshoot", "failure", "metrics", "observability", "security", "automation", "testing", "feature flag", "canary"]):
        score += 1.5
        evidence.positive.append("Answer includes production or engineering signals.")

    if any(word in answer for word in ["i did", "we did", "implemented", "built", "designed", "deployed", "owned"]):
        score += 1.0
        evidence.positive.append("Answer suggests hands-on ownership.")

    if len(answer) > 250:
        score += 0.5
        evidence.positive.append("Answer has sufficient detail.")

    score = min(score, 5.0)
    level = _score_to_level(score)

    follow_ups = []
    if score < 3.5:
        follow_ups.append(f"Can you give a concrete example for {comp_def.label}?")
    if score < 4.5:
        follow_ups.append(f"What trade-offs did you consider in {comp_def.label}?")

    return CompetencyScore(
        key=comp_def.key,
        label=comp_def.label,
        score=score,
        level=level,
        evidence=evidence,
        summary=f"{comp_def.label}: {level} ({score}/5)",
        follow_up_questions=follow_ups,
    )


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Ollama sometimes wraps JSON in markdown fences or adds stray
    text around it. Try direct parse first, then fall back to pulling
    out the first {...} block."""
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


def _ollama_score_competency(
    answer: str, comp_def: CompetencyDefinition, role_label: str, role: str, candidate_id: str = ""
) -> Optional[CompetencyScore]:
    """Ask Ollama to judge the answer against real reference technical
    knowledge, not just keyword-match it. Returns None on any failure
    so the caller can fall back to the rule-based scorer.

    Uses get_reference_for_specific_question() rather than the older
    per-competency blob: since question selection is a deterministic
    hash of (candidate_id, role, competency_key), replaying that same
    hash here recovers the EXACT question this candidate was asked, so
    scoring can use that one question's specific reference answers
    instead of a generic mix covering every possible variant. Falls
    back automatically to the old per-competency blob for any
    role/competency without per-question data yet.

    The "consulting" competency is a genuinely different kind of
    question - a behavioral/consulting story with no technical
    reference answer to grade against - so it gets its own prompt
    entirely, judging communication and specificity rather than
    technical correctness. Using the same "expert answer key" framing
    for it would be actively wrong (there's no engineering soundness
    to judge in a story about a disagreement with a teammate)."""
    if comp_def.key == CompetencyKey.consulting:
        prompt = f"""You are an interviewer assessing a candidate's communication skills based on a behavioral/consulting question, for a {role_label} role.

This is NOT a technical question. There is no "correct" answer to grade against. Judge the answer purely on:
- Whether the candidate gives a real, specific example (a real situation, what they actually did, what happened) rather than a vague generality or a hypothetical/textbook answer
- Clarity of communication - is the answer easy to follow, well-structured, and specific rather than rambling or evasive
- Whether they actually answered the question that was asked, rather than talking around it

Question asked: {comp_def.prompt}

Candidate's answer:
\"\"\"{answer if answer else "(no answer provided)"}\"\"\"

Score the candidate's answer from 0 to 5 based on communication quality and specificity of example - NOT technical correctness, since there is none to assess here.

Respond with ONLY a single JSON object, no markdown formatting, no code fences, no extra text, in exactly this shape:
{{"score": <number 0-5>, "positive": ["<short evidence point>"], "gaps": ["<short gap point>"], "summary": "<one sentence>"}}
"""
    else:
        reference = get_reference_for_specific_question(role, comp_def.key.value, candidate_id)

        prompt = f"""You are an interviewer scoring a candidate's answer for a {role_label} role.

Competency being assessed: {comp_def.label}
What this competency covers: {comp_def.prompt}

Reference knowledge (the "expert answer key" - use this to judge accuracy, do not just check for keyword overlap):
{reference if reference else "No specific reference material - judge on general engineering soundness."}

Candidate's answer:
\"\"\"{answer if answer else "(no answer provided)"}\"\"\"

Score the candidate's answer from 0 to 5 based on how well it demonstrates real understanding of the correct mechanics, not just mentioning the right buzzwords.

Respond with ONLY a single JSON object, no markdown formatting, no code fences, no extra text, in exactly this shape:
{{"score": <number 0-5>, "positive": ["<short evidence point>"], "gaps": ["<short gap point>"], "summary": "<one sentence>"}}
"""

    try:
        raw = generate_with_ollama(prompt, timeout=OLLAMA_SCORING_TIMEOUT_SECONDS)
        parsed = _extract_json(raw)

        if not parsed or "score" not in parsed:
            return None

        score = float(parsed["score"])
        score = max(0.0, min(score, 5.0))
        level = _score_to_level(score)

        evidence = SkillEvidence(
            positive=[str(p) for p in parsed.get("positive", [])][:5],
            gaps=[str(g) for g in parsed.get("gaps", [])][:5],
            risk_flags=[],
        )

        if not answer:
            evidence.risk_flags.append("No evidence")

        follow_ups = []
        if score < 3.5:
            follow_ups.append(f"Can you give a concrete example for {comp_def.label}?")
        if score < 4.5 and comp_def.key != CompetencyKey.consulting:
            follow_ups.append(f"What trade-offs did you consider in {comp_def.label}?")

        summary = parsed.get("summary") or f"{comp_def.label}: {level} ({score}/5)"

        return CompetencyScore(
            key=comp_def.key,
            label=comp_def.label,
            score=score,
            level=level,
            evidence=evidence,
            summary=summary,
            follow_up_questions=follow_ups,
        )
    except Exception:
        # Any failure (timeout, connection refused, bad JSON, etc.)
        # falls back to the rule-based scorer - never breaks the demo.
        return None


def analyze_assessment(
    payload: CandidateAssessmentRequest,
    competency_defs: List[CompetencyDefinition],
    role_slug: str = "operability-engineer",
) -> CandidateAssessmentResponse:
    competencies: List[CompetencyScore] = []
    used_ollama_count = 0

    for comp_def in competency_defs:
        answer = (payload.answers.get(comp_def.key.value, "") or "").strip()

        result = _ollama_score_competency(answer, comp_def, payload.role, role_slug, payload.candidate_id)
        if result is not None:
            used_ollama_count += 1
        else:
            result = _rule_based_score(answer.lower(), comp_def)

        competencies.append(result)

    overall = round(sum(c.score for c in competencies) / len(competencies), 2)

    if overall >= 4.0:
        recommendation = Recommendation.strong_match
    elif overall >= 2.8:
        recommendation = Recommendation.review
    else:
        recommendation = Recommendation.reject

    scoring_model = (
        "ollama_llm"
        if used_ollama_count == len(competencies)
        else "ollama_llm_partial_fallback"
        if used_ollama_count > 0
        else "rule_based_fallback"
    )

    return CandidateAssessmentResponse(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        role=payload.role,
        stage=payload.stage,
        competencies=competencies,
        overall_score=overall,
        recommendation=recommendation,
        notes="Scored against reference production knowledge using the local LLM, with rule-based fallback for reliability.",
        metadata={
            "competency_count": len(competencies),
            "scoring_model": scoring_model,
            "ollama_scored_count": used_ollama_count,
        },
    )