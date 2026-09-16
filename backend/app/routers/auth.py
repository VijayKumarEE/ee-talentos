from fastapi import APIRouter, HTTPException, Body, Request

from app.recruiters import get_recruiter_by_email
from app.auth_service import create_session, delete_session
from app.rate_limiter import check_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: Request, email: str = Body(..., embed=True)):
    # Keyed by client IP rather than the submitted email, since an
    # email-keyed limit is trivially sidestepped by just trying a
    # different email each time. 10 attempts/minute is generous for a
    # real recruiter (nobody logs in that often) but stops naive
    # automated hammering of the allowlist.
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"login:{client_ip}", max_attempts=10, window_seconds=60)

    recruiter = get_recruiter_by_email(email)

    if not recruiter:
        raise HTTPException(
            status_code=403,
            detail="This email is not on the approved recruiter list.",
        )

    # Issue a real session token - this is what every recruiter-only
    # route now checks for, instead of trusting whatever the frontend
    # chooses to show.
    session = create_session(recruiter["email"], recruiter["name"], recruiter["slug"])

    return {
        "email": recruiter["email"],
        "name": recruiter["name"],
        "slug": recruiter["slug"],
        "token": session["token"],
        "expires_at": session["expires_at"],
    }


@router.post("/logout")
def logout(token: str = Body(..., embed=True)):
    """Invalidates the session server-side, not just client-side. Never
    errors even if the token is already gone - logout should always
    look successful to the person clicking it."""
    delete_session(token)
    return {"message": "Logged out"}