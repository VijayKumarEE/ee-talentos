"""
Real recruiter session management, backed by SQLite (survives restarts,
same reasoning as store.py).

Before this file existed, /auth/login checked the email allowlist and
returned recruiter info, but nothing was actually issued or checked
afterwards - every recruiter route was reachable by anyone who knew the
URL. This file is what makes a login session real: a random opaque
token is created on login, stored server-side with an expiry, and every
recruiter-only route (via auth_dependency.get_current_recruiter) must
present a valid, unexpired token to proceed.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from app.database import SessionLocal
from app.models import RecruiterSession

# A recruiter logging in at the start of a workday shouldn't have to
# re-login before lunch, but a token also shouldn't stay valid forever.
SESSION_LIFETIME_HOURS = 12


def create_session(email: str, name: str, slug: str) -> dict:
    """Called on successful /auth/login. Returns the new token plus its
    expiry so the frontend can store both."""
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=SESSION_LIFETIME_HOURS)

    db = SessionLocal()
    try:
        row = RecruiterSession(
            token=token,
            recruiter_email=email,
            recruiter_name=name,
            recruiter_slug=slug,
            created_at=now,
            expires_at=expires_at,
        )
        db.add(row)
        db.commit()
    finally:
        db.close()

    return {"token": token, "expires_at": expires_at.isoformat()}


def get_recruiter_for_token(token: str) -> Optional[dict]:
    """Looks up a token and returns the recruiter it belongs to, or
    None if the token is missing, unknown, or expired. An expired
    session is deleted on the way out, so expired rows don't pile up."""
    if not token:
        return None

    db = SessionLocal()
    try:
        row = (
            db.query(RecruiterSession)
            .filter(RecruiterSession.token == token)
            .first()
        )
        if not row:
            return None

        if row.expires_at < datetime.utcnow():
            db.delete(row)
            db.commit()
            return None

        return {
            "email": row.recruiter_email,
            "name": row.recruiter_name,
            "slug": row.recruiter_slug,
        }
    finally:
        db.close()


def delete_session(token: str) -> None:
    """Called on /auth/logout so a logged-out token can't still be
    used if it leaked somewhere (browser history, a shared link, etc).
    Silently does nothing if the token doesn't exist - logout should
    never fail from the user's perspective."""
    if not token:
        return

    db = SessionLocal()
    try:
        row = (
            db.query(RecruiterSession)
            .filter(RecruiterSession.token == token)
            .first()
        )
        if row:
            db.delete(row)
            db.commit()
    finally:
        db.close()