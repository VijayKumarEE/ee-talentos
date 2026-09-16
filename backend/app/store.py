"""
Persistent stores backed by SQLite.

CandidateStore keeps the same dict-like interface the routers were
already written against (CANDIDATES[id] = {...}, CANDIDATES.get(id),
"x" in CANDIDATES, del CANDIDATES[id]) so candidates.py / assessments.py
/ scheduling.py need almost no changes. Under the hood, though, the
handful of fields that are actually filtered/sorted on (role, recruiter,
stage, created_at) now live in real indexed columns instead of being
buried inside one opaque JSON blob - see models.py.

Anything reading/writing a candidate via CANDIDATES[id] still sees one
flat dict, same shape as before. The new list_candidates() method is
what dashboard.py should use instead of iterating .items() and
filtering in Python - it pushes the role/recruiter filter down into a
real SQL WHERE clause on indexed columns.

ASSESSMENTS is untouched - still a plain JSON-blob SQLDict, since
assessments are always read/written whole and never filtered
independently, so there's no benefit to breaking them into columns.
"""

from datetime import datetime
from typing import Optional

from app.database import SessionLocal, engine, Base
from app.models import Candidate, Assessment

# Create tables on import if they don't exist yet.
Base.metadata.create_all(bind=engine)

# Fields promoted to real columns on the Candidate table. Anything else
# in a candidate dict is stored inside the `details` JSON column.
_CANDIDATE_COLUMN_FIELDS = {
    "full_name",
    "email",
    "role_applied_for",
    "recruiter_slug",
    "stage",
}


def _split_candidate_fields(value: dict) -> dict:
    """Returns just the subset of `value` that maps to real columns.
    (candidate_id and created_at are handled separately - candidate_id
    is the key, not a field on the dict's value; created_at is set
    once at creation and never overwritten by later saves.)"""
    return {k: value.get(k) for k in _CANDIDATE_COLUMN_FIELDS if k in value}


def _merge_candidate_row(row: Candidate) -> dict:
    """Reconstructs the flat dict shape routers expect: details blob
    plus the real columns overlaid on top, so callers can't tell (or
    need to care) which fields are columns vs JSON."""
    merged = dict(row.details or {})
    merged["candidate_id"] = row.candidate_id
    for field in _CANDIDATE_COLUMN_FIELDS:
        merged[field] = getattr(row, field)
    merged["created_at"] = row.created_at.isoformat() if row.created_at else None
    return merged


class CandidateStore:
    def __setitem__(self, key, value: dict):
        db = SessionLocal()
        try:
            row = db.query(Candidate).filter(Candidate.candidate_id == key).first()
            column_fields = _split_candidate_fields(value)
            details = {k: v for k, v in value.items() if k not in _CANDIDATE_COLUMN_FIELDS and k != "candidate_id"}

            if row:
                for field, val in column_fields.items():
                    setattr(row, field, val)
                row.details = details
            else:
                row = Candidate(
                    candidate_id=key,
                    created_at=datetime.utcnow(),
                    details=details,
                    **column_fields,
                )
                db.add(row)
            db.commit()
        finally:
            db.close()

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key) -> bool:
        db = SessionLocal()
        try:
            row = db.query(Candidate).filter(Candidate.candidate_id == key).first()
            return row is not None
        finally:
            db.close()

    def __delitem__(self, key):
        db = SessionLocal()
        try:
            row = db.query(Candidate).filter(Candidate.candidate_id == key).first()
            if row:
                db.delete(row)
                db.commit()
        finally:
            db.close()

    def get(self, key, default=None):
        db = SessionLocal()
        try:
            row = db.query(Candidate).filter(Candidate.candidate_id == key).first()
            return _merge_candidate_row(row) if row else default
        finally:
            db.close()

    def items(self):
        """Kept for backward compatibility. Prefer list_candidates()
        for anything that needs to filter - this loads the whole table."""
        db = SessionLocal()
        try:
            rows = db.query(Candidate).all()
            return [(row.candidate_id, _merge_candidate_row(row)) for row in rows]
        finally:
            db.close()

    def values(self):
        return [value for _, value in self.items()]

    def keys(self):
        return [key for key, _ in self.items()]

    def list_candidates(self, role_applied_for: Optional[str] = None, recruiter_slug: Optional[str] = None):
        """Real SQL-filtered, indexed query - used by the recruiter
        dashboard instead of loading every candidate and filtering in
        Python. Newest applicants first."""
        db = SessionLocal()
        try:
            query = db.query(Candidate)
            if role_applied_for:
                query = query.filter(Candidate.role_applied_for == role_applied_for)
            if recruiter_slug:
                query = query.filter(Candidate.recruiter_slug == recruiter_slug)
            query = query.order_by(Candidate.created_at.desc())
            rows = query.all()
            return [_merge_candidate_row(row) for row in rows]
        finally:
            db.close()


class SQLDict:
    """Unchanged generic JSON-blob dict store, still used for ASSESSMENTS."""

    def __init__(self, model, key_column: str):
        self._model = model
        self._key_column = key_column

    def __setitem__(self, key, value: dict):
        db = SessionLocal()
        try:
            row = (
                db.query(self._model)
                .filter(getattr(self._model, self._key_column) == key)
                .first()
            )
            if row:
                row.data = value
            else:
                row = self._model(**{self._key_column: key, "data": value})
                db.add(row)
            db.commit()
        finally:
            db.close()

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key) -> bool:
        db = SessionLocal()
        try:
            row = (
                db.query(self._model)
                .filter(getattr(self._model, self._key_column) == key)
                .first()
            )
            return row is not None
        finally:
            db.close()

    def __delitem__(self, key):
        db = SessionLocal()
        try:
            row = (
                db.query(self._model)
                .filter(getattr(self._model, self._key_column) == key)
                .first()
            )
            if row:
                db.delete(row)
                db.commit()
        finally:
            db.close()

    def get(self, key, default=None):
        db = SessionLocal()
        try:
            row = (
                db.query(self._model)
                .filter(getattr(self._model, self._key_column) == key)
                .first()
            )
            return row.data if row else default
        finally:
            db.close()

    def items(self):
        db = SessionLocal()
        try:
            rows = db.query(self._model).all()
            return [(getattr(row, self._key_column), row.data) for row in rows]
        finally:
            db.close()

    def values(self):
        return [value for _, value in self.items()]

    def keys(self):
        return [key for key, _ in self.items()]


CANDIDATES = CandidateStore()
ASSESSMENTS = SQLDict(Assessment, "candidate_id")