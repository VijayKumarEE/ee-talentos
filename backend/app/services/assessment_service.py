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
from app.providers.ai_provider import get_ai_provider

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


def _competency_score_from_llm_result(
    parsed: Dict[str, Any], comp_def: CompetencyDefinition, answer: str
) -> Optional[CompetencyScore]:
    """Turns one provider result ({"score", "positive", "gaps",
    "summary"}) into a CompetencyScore. Shared by both providers so
    the actual grading rules (level mapping, follow-up-question
    thresholds) are identical regardless of whether the judgment came
    from Ollama or OpenRouter."""
    if not parsed or "score" not in parsed:
        return None

    try:
        score = float(parsed["score"])
    except (TypeError, ValueError):
        return None

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


def analyze_assessment(
    payload: CandidateAssessmentRequest,
    competency_defs: List[CompetencyDefinition],
    role_slug: str = "operability-engineer",
) -> CandidateAssessmentResponse:
    competencies: List[CompetencyScore] = []
    used_llm_count = 0

    # One provider call covers every competency (Ollama loops internally
    # per-competency, unchanged; OpenRouter makes exactly one combined
    # request - see providers/ai_provider.py for why).
    provider = get_ai_provider()
    llm_results = provider.score_all(
        competency_defs, payload.answers, payload.role, role_slug, payload.candidate_id
    )

    for comp_def in competency_defs:
        answer = (payload.answers.get(comp_def.key.value, "") or "").strip()

        parsed = llm_results.get(comp_def.key.value)
        result = _competency_score_from_llm_result(parsed, comp_def, answer) if parsed else None
        if result is not None:
            used_llm_count += 1
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
        "llm_scored"
        if used_llm_count == len(competencies)
        else "llm_partial_fallback"
        if used_llm_count > 0
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
            "llm_scored_count": used_llm_count,
        },
    )