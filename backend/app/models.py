from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, JSON
from app.database import Base


class Candidate(Base):
    """Candidate record.

    Only the fields actually filtered/sorted on by the dashboard get a
    real column (with an index where it matters): role_applied_for,
    recruiter_slug, stage, created_at. full_name/email are columns too
    since they're commonly displayed/searched. Everything else
    (salary fields, location, assessment_questions, assessment_progress,
    scheduling, recruiter_review, etc.) lives in `details` as JSON,
    exactly like before, since it's always read/written as a whole
    blob per candidate and never queried independently.

    This means dashboard.py can now do a real indexed SQL WHERE clause
    for role/recruiter filtering instead of loading every candidate
    into Python and filtering there.
    """

    __tablename__ = "candidates"

    candidate_id = Column(String, primary_key=True, index=True)

    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    role_applied_for = Column(String, nullable=True, index=True)
    recruiter_slug = Column(String, nullable=True, index=True)
    stage = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    details = Column(JSON, nullable=False, default=dict)


class Assessment(Base):
    """Unchanged: always read/written as one blob keyed by candidate_id,
    never filtered/queried independently, so a JSON column is the right
    fit here (unlike Candidate)."""

    __tablename__ = "assessments"

    candidate_id = Column(String, primary_key=True, index=True)
    data = Column(JSON, nullable=False)


class RecruiterSession(Base):
    """A real server-side session, created on successful /auth/login
    and checked by every recruiter-only route via get_current_recruiter.
    Before this, /auth/login just returned recruiter info with nothing
    to stop a direct API call to any recruiter route - this table is
    what makes the login actually mean something."""

    __tablename__ = "recruiter_sessions"

    token = Column(String, primary_key=True, index=True)
    recruiter_email = Column(String, nullable=False)
    recruiter_name = Column(String, nullable=False)
    recruiter_slug = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)