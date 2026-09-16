"""
Database engine selection.

LOCAL MODE (default, APP_MODE=local): unchanged - a local SQLite file
(mvp.db), zero setup, works fully offline.

CLOUD MODE (APP_MODE=cloud): points the exact same SQLAlchemy models
(app/models.py) and the exact same store.py logic at Supabase's
Postgres database instead, via a direct connection string
(SUPABASE_DB_URL). This is deliberately NOT a rewrite to Supabase's
REST API - store.py's CandidateStore/SQLDict classes, and every router
that uses CANDIDATES/ASSESSMENTS, work completely unchanged against
Postgres. Only this one file decides which database engine the rest
of the app is actually talking to.

Why a direct Postgres connection instead of Supabase's REST API:
- It's the smallest possible change (models.py, store.py: zero edits).
- SQLAlchemy already abstracts SQLite vs Postgres for us (JSON columns,
  querying, etc. all work the same way on both).
- It avoids reinventing filtering/pagination that store.py already does
  well against SQLite.

Because the backend is the only thing that ever holds this connection
string (it's a backend-only env var, never sent to the browser), this
also naturally satisfies "the Supabase service-role key must never
reach the frontend" - the frontend never talks to Postgres directly at
all, only to the FastAPI backend over HTTPS.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import IS_CLOUD_MODE, SUPABASE_DB_URL

if IS_CLOUD_MODE:
    if not SUPABASE_DB_URL:
        raise RuntimeError(
            "APP_MODE=cloud but SUPABASE_DB_URL is not set. Copy the "
            "'Connection string' (Transaction pooler recommended) from "
            "Supabase -> Project Settings -> Database, and set it as "
            "SUPABASE_DB_URL in backend/.env."
        )
    SQLALCHEMY_DATABASE_URL = SUPABASE_DB_URL
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,  # free-tier/pooled Postgres connections can go
        # stale between requests (e.g. after Render's free instance sleeps);
        # pre-ping detects that and reconnects instead of raising.
    )
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./mvp.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
