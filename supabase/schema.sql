-- EE TalentOS - Supabase Postgres schema (CLOUD MODE)
--
-- You normally do NOT need to run this by hand: when the backend
-- starts with APP_MODE=cloud, SQLAlchemy (Base.metadata.create_all in
-- app/store.py / app/auth_service.py) creates these same tables
-- automatically on first run, the same way it does against local
-- SQLite. This file exists so you can:
--   1. See exactly what will be created, before it happens.
--   2. Create the tables manually up front from the Supabase SQL
--      editor if you prefer not to rely on auto-create-on-first-run.
--   3. Re-create them if you ever need to reset the cloud database.
--
-- This mirrors the ACTUAL existing schema in backend/app/models.py -
-- nothing here is invented; it's the same entities the local SQLite
-- app already uses (candidates, assessments, recruiter sessions),
-- plus one new table (ai_usage_log) for the cost-control feature.
--
-- A NOTE ON ROW LEVEL SECURITY (RLS):
-- The backend connects to this database with a direct Postgres
-- connection string (SUPABASE_DB_URL) as a trusted server - it is NOT
-- using Supabase's public REST API with the anon key. Browsers never
-- talk to this database directly. Because of that, Postgres RLS
-- policies are NOT the security boundary here (RLS applies to
-- PostgREST/anon-key access) - the security boundary is: only the
-- FastAPI backend holds this connection string, and FastAPI's own
-- routes (get_current_recruiter, candidate-scoped lookups) decide who
-- can read what. RLS is enabled below anyway as defense-in-depth in
-- case this project ever also exposes these tables via Supabase's
-- REST API directly - if you never do that, it has no practical
-- effect on the app.

create table if not exists candidates (
    candidate_id     text primary key,
    full_name        text,
    email            text,
    role_applied_for text,
    recruiter_slug   text,
    stage            text,
    created_at       timestamptz not null default now(),
    details          jsonb not null default '{}'::jsonb
);

create index if not exists ix_candidates_email on candidates (email);
create index if not exists ix_candidates_role_applied_for on candidates (role_applied_for);
create index if not exists ix_candidates_recruiter_slug on candidates (recruiter_slug);
create index if not exists ix_candidates_stage on candidates (stage);
create index if not exists ix_candidates_created_at on candidates (created_at);

create table if not exists assessments (
    candidate_id text primary key references candidates (candidate_id) on delete cascade,
    data         jsonb not null
);

create table if not exists recruiter_sessions (
    token           text primary key,
    recruiter_email text not null,
    recruiter_name  text not null,
    recruiter_slug  text not null,
    created_at      timestamptz not null default now(),
    expires_at      timestamptz not null
);

create index if not exists ix_recruiter_sessions_expires_at on recruiter_sessions (expires_at);

create table if not exists ai_usage_log (
    id           bigserial primary key,
    created_at   timestamptz not null default now(),
    candidate_id text,
    call_type    text not null, -- 'assessment' | 'transcription' | 'resume_extraction'
    model        text,
    cost_usd     double precision,
    success      boolean not null default true
);

create index if not exists ix_ai_usage_log_created_at on ai_usage_log (created_at);
create index if not exists ix_ai_usage_log_candidate_id on ai_usage_log (candidate_id);

alter table candidates enable row level security;
alter table assessments enable row level security;
alter table recruiter_sessions enable row level security;
alter table ai_usage_log enable row level security;

-- No policies are created (default-deny): since the backend connects
-- with the direct database connection string (bypassing PostgREST/RLS
-- entirely), this default-deny posture only matters if these tables
-- are ever queried through Supabase's REST API/anon key - which this
-- app does not do. If you later want recruiters or candidates to read
-- these tables directly from the browser via Supabase's client SDK
-- (bypassing FastAPI), you would need to add explicit policies here
-- first - do not do this without deciding exactly what each role
-- should see, since `details`/`data` contain private candidate
-- information (resume text fields, transcripts, AI assessments).

-- ---------------------------------------------------------------------
-- Storage buckets (resumes, recordings) - PRIVATE, not public.
-- You can also create these from the Dashboard (Storage -> New bucket,
-- toggle "Public bucket" OFF) if you prefer a UI - this does the same
-- thing. Do not tick "Public bucket" for either of these: the backend
-- serves files back only via short-lived signed URLs
-- (app/providers/storage_provider.py), and a public bucket would
-- bypass that entirely.
insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('recordings', 'recordings', false)
on conflict (id) do nothing;

