"""
A minimal in-memory rate limiter for a single-process MVP.

This is deliberately simple: an in-memory dict keyed by whatever the
caller passes in (e.g. a client IP), pruned on each check. It is NOT
meant to survive a server restart, and it does NOT work correctly if
this app is ever run with multiple uvicorn workers or processes (each
worker would keep its own separate counts) - if that ever happens,
this needs to move to a shared store like Redis instead. For a
handful of recruiters hitting a single dev/demo server, this is
enough to stop naive automated hammering of /auth/login without
adding new infrastructure.
"""

import time
from collections import defaultdict
from typing import Dict, List

from fastapi import HTTPException

_attempts: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(key: str, max_attempts: int, window_seconds: int) -> None:
    """Raises HTTPException(429) if `key` has been checked more than
    `max_attempts` times within the last `window_seconds`. Otherwise
    records this attempt and returns normally."""
    now = time.time()
    attempts = _attempts[key]

    cutoff = now - window_seconds
    attempts[:] = [t for t in attempts if t > cutoff]

    if len(attempts) >= max_attempts:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please wait a minute and try again.",
        )

    attempts.append(now)