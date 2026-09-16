"""
Application-level cost protection for CLOUD MODE's OpenRouter usage.

This is intentionally simple (a single log table + two counts) - not a
billing system. Two independent ceilings, either of which stops new
calls until next calendar month:

1. AI_MONTHLY_BUDGET_USD - a soft $ ceiling, checked against the sum of
   `cost_usd` OpenRouter reported for this month's calls (when
   OpenRouter includes usage/cost in its response; not all models do).
2. AI_MAX_ASSESSMENT_CALLS_PER_MONTH - a hard ceiling on the number of
   assessment-scoring calls, regardless of whether cost reporting is
   available - a safety net so a reporting gap can't let usage run
   away unnoticed.

This does NOT replace setting a real spend limit in your OpenRouter
account (Settings -> Limits) - that is the only hard backstop. This
module is about avoiding *accidental* waste (duplicate calls, runaway
retries), not enforcing a contractual cap.

LOCAL MODE never touches this - Ollama is free and unmetered.
"""

from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models import AIUsageLog
from app.config import AI_MONTHLY_BUDGET_USD, AI_MAX_ASSESSMENT_CALLS_PER_MONTH


class BudgetExceeded(Exception):
    """Raised when a new OpenRouter call would exceed a configured
    monthly ceiling. Callers should catch this and fall back to a
    safe error state (see routers/assessments.py) rather than let it
    propagate as a raw 500."""


def _month_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)


def get_monthly_usage() -> dict:
    """Returns this calendar month's usage so far: total (known) cost
    and call counts by type. Used both to enforce the ceilings and to
    show a simple usage report."""
    db = SessionLocal()
    try:
        rows = (
            db.query(AIUsageLog)
            .filter(AIUsageLog.created_at >= _month_start())
            .all()
        )
        total_cost = sum((r.cost_usd or 0.0) for r in rows)
        assessment_calls = sum(1 for r in rows if r.call_type == "assessment")
        transcription_calls = sum(1 for r in rows if r.call_type == "transcription")
        return {
            "total_cost_usd": round(total_cost, 4),
            "assessment_calls": assessment_calls,
            "transcription_calls": transcription_calls,
            "total_calls": len(rows),
            "budget_usd": AI_MONTHLY_BUDGET_USD,
            "max_assessment_calls": AI_MAX_ASSESSMENT_CALLS_PER_MONTH,
        }
    finally:
        db.close()


def check_budget_or_raise(call_type: str) -> None:
    """Call BEFORE making an OpenRouter request. Raises BudgetExceeded
    if either ceiling has already been reached this month."""
    usage = get_monthly_usage()

    if usage["total_cost_usd"] >= AI_MONTHLY_BUDGET_USD:
        raise BudgetExceeded(
            f"Monthly AI budget of ${AI_MONTHLY_BUDGET_USD:.2f} reached "
            f"(${usage['total_cost_usd']:.2f} spent so far this month)."
        )

    if call_type == "assessment" and usage["assessment_calls"] >= AI_MAX_ASSESSMENT_CALLS_PER_MONTH:
        raise BudgetExceeded(
            f"Monthly assessment-call limit of {AI_MAX_ASSESSMENT_CALLS_PER_MONTH} reached."
        )


def log_usage(
    call_type: str,
    candidate_id: Optional[str] = None,
    model: Optional[str] = None,
    cost_usd: Optional[float] = None,
    success: bool = True,
) -> None:
    """Records one OpenRouter call for the monthly usage report and
    budget enforcement. Never raises - a logging failure must never
    break the actual assessment/transcription flow."""
    db = SessionLocal()
    try:
        db.add(
            AIUsageLog(
                created_at=datetime.utcnow(),
                candidate_id=candidate_id,
                call_type=call_type,
                model=model,
                cost_usd=cost_usd,
                success=success,
            )
        )
        db.commit()
        print(
            f"[cost_guard] {call_type} call logged "
            f"(candidate={candidate_id}, model={model}, "
            f"cost={'$%.4f' % cost_usd if cost_usd is not None else 'unknown'}, "
            f"success={success})"
        )
    except Exception as exc:  # noqa: BLE001 - logging must never break the caller
        print(f"[cost_guard] Failed to log usage: {exc}")
    finally:
        db.close()
