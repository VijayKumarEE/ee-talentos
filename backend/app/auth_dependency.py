"""
FastAPI dependency that protects recruiter-only routes.

Attach this to any route that only a logged-in recruiter should be
able to call, e.g.:

    @router.get("/recruiter")
    def recruiter_dashboard(..., _recruiter: dict = Depends(get_current_recruiter)):
        ...

It accepts the session token two ways:
1. `Authorization: Bearer <token>` header - used by every normal
   fetch() call from the frontend's api/client.ts.
2. `?token=<token>` query parameter - needed specifically for the
   resume and recording download routes, which the frontend links to
   directly via window.open()/<video src="...">. A browser navigating
   to a URL or loading a <video> source cannot attach a custom header,
   so a query-string token is the pragmatic way to protect a
   direct-link download without breaking playback. This mirrors how
   real signed-URL downloads work elsewhere (e.g. S3 pre-signed URLs).
"""

from typing import Optional

from fastapi import Header, HTTPException, Query

from app.auth_service import get_recruiter_for_token


def get_current_recruiter(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
) -> dict:
    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization[len("bearer "):].strip()

    effective_token = bearer_token or token
    recruiter = get_recruiter_for_token(effective_token) if effective_token else None

    if not recruiter:
        raise HTTPException(
            status_code=401,
            detail="Not logged in or your session has expired. Please log in again.",
        )

    return recruiter