# EE TalentOS - Cloud Demo Deployment Guide

This document is for the `cloud-demo` branch only. Your original local
app is untouched on `main` - see section H for how to confirm that.

Everything below assumes you're starting from zero on Supabase, Render,
GitHub Pages, and OpenRouter.

---

## A. Files changed / added

**Changed** (behavior identical in LOCAL MODE; new behavior only activates when `APP_MODE=cloud`):
- `backend/app/config.py` - new cloud env vars (all optional, default to local behavior)
- `backend/app/database.py` - picks SQLite or Supabase Postgres based on `APP_MODE`
- `backend/app/main.py` - CORS now mode-aware; added `/admin/ai-usage`
- `backend/app/models.py` - added `AIUsageLog` table (cost tracking)
- `backend/app/routers/assessments.py` - recordings go through the storage/transcription providers; added duplicate-processing guards
- `backend/app/routers/candidates.py` - resumes go through the storage provider
- `backend/app/services/assessment_service.py` - scoring now goes through the AI provider (business logic/rules unchanged)
- `backend/app/services/github_showcase_service.py` - removed email/phone from the public showcase payload (privacy fix, see section 15 of your brief)
- `backend/app/services/resume_parsing_service.py` - contextual field extraction now goes through the AI provider
- `backend/app/services/transcription_service.py` - ffmpeg lookup now also checks the bundled `imageio-ffmpeg` binary (needed for cloud hosts with no system ffmpeg)
- `backend/requirements.txt` - added `psycopg2-binary`, `imageio-ffmpeg`
- `frontend/src/App.tsx` - `BrowserRouter` -> `HashRouter` (GitHub Pages refresh-safe)
- `frontend/src/api/client.ts`, `frontend/src/pages/RecruiterShortlistPage.tsx` - API base URL now reads `VITE_API_BASE_URL`
- `frontend/vite.config.ts` - configurable build base path

**New:**
- `backend/app/providers/ai_provider.py`, `transcription_provider.py`, `storage_provider.py`
- `backend/app/cost_guard.py`
- `backend/.env.example`, `backend/.gitignore`
- `frontend/.env.example`, `frontend/src/vite-env.d.ts`
- `supabase/schema.sql`
- `render.yaml`
- `.github/workflows/deploy-pages.yml`
- `CLOUD_DEPLOYMENT.md` (this file)

**Untouched:** everything else, including all question-bank content, business rules (7.5-year bar, stage machine, recruiter auth model), and the entire showcase front-end (`showcase-site-source/`).

---

## B. What changed, in plain language

- The app now has a single switch, `APP_MODE` (`local` or `cloud`), in `backend/.env`. Local behavior is 100% unchanged when this is `local` (the default).
- In cloud mode, four things get swapped for cloud equivalents: the database (SQLite -> Supabase Postgres), file storage (local disk -> Supabase Storage), AI scoring (Ollama -> OpenRouter), and transcription (faster-whisper -> OpenRouter). The actual scoring rules, question logic, stage machine, and recruiter workflow are identical either way.
- To control AI cost, the cloud version asks OpenRouter to score all 3 assessment questions in **one** request instead of three, and tracks a monthly budget + call count so it can't run away.
- If a candidate refreshes or re-submits a recording, it will NOT trigger another paid transcription/scoring call unless you explicitly ask for a retry.
- Fixed a privacy gap: the public GitHub showcase was receiving candidate email and phone number. It no longer does, in either mode.
- The frontend now reads the backend's address from a setting instead of having it hard-coded, and switched to a routing method that won't break when a recruiter refreshes the page on GitHub Pages.

---

## C. Supabase setup

1. Create a free project at supabase.com.
2. **Database**: Project Settings -> Database -> Connection string -> copy the "Transaction pooler" URI (recommended for Render's free tier). This is your `SUPABASE_DB_URL`.
3. Run `supabase/schema.sql` in the SQL Editor (Supabase Dashboard -> SQL Editor -> paste -> Run). This creates the tables and the two private storage buckets (`resumes`, `recordings`). If you skip this, the tables will still auto-create the first time the backend starts - but the storage buckets will NOT auto-create, so run at least the two `insert into storage.buckets` statements at the bottom of that file.
4. **API keys**: Project Settings -> API. Copy:
   - `Project URL` -> `SUPABASE_URL`
   - `anon public` key -> `SUPABASE_ANON_KEY` (not currently used by the backend, but harmless to set)
   - `service_role` key -> `SUPABASE_SERVICE_ROLE_KEY` (**backend only - never in the frontend**)
5. Confirm both buckets (`resumes`, `recordings`) show "Public: No" in Storage.

## D. Render setup

1. Push this repo (the `cloud-demo` branch) to GitHub.
2. Render dashboard -> New -> Blueprint -> connect the repo -> Render reads `render.yaml` and proposes `ee-talentos-backend` on the free plan.
3. After creation, open the service -> Environment -> fill in the values marked `sync: false` in `render.yaml`: `SUPABASE_DB_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENROUTER_API_KEY`, `CORS_ORIGINS` (set this once you know your GitHub Pages URL from step E), and the `GITHUB_*` values from your existing showcase setup.
4. Deploy. Note the resulting URL, e.g. `https://ee-talentos-backend.onrender.com` - you need this for step E.
5. **Free tier note**: this service sleeps after ~15 minutes idle and takes 30-60 seconds to wake on the next request. The first candidate/recruiter action after a quiet period will just be slow, not broken - consider mentioning this once to your team.

## E. GitHub Pages setup

1. Repo Settings -> Pages -> Source -> "GitHub Actions".
2. Repo Settings -> Secrets and variables -> Actions -> Variables tab -> New repository variable: `VITE_API_BASE_URL` = your Render URL from step D.
3. Push to the `cloud-demo` branch (or run the workflow manually from the Actions tab) - `.github/workflows/deploy-pages.yml` builds and deploys automatically.
4. Your app will be live at `https://<your-username>.github.io/<repo-name>/#/apply` (candidate) and `.../#/recruiter` (recruiter) - note the `#`, from the GitHub-Pages-safe routing change.
5. Go back to Render and set `CORS_ORIGINS` to `https://<your-username>.github.io` (no trailing path/hash), then redeploy the backend.

## F. Environment variables

| Variable | Where it goes | What you put there |
|---|---|---|
| `APP_MODE` | Render | `cloud` |
| `SUPABASE_DB_URL` | Render | Supabase connection string (step C.2) |
| `SUPABASE_URL` | Render | Supabase project URL (step C.4) |
| `SUPABASE_ANON_KEY` | Render | Supabase anon key (step C.4) |
| `SUPABASE_SERVICE_ROLE_KEY` | Render | Supabase service-role key (step C.4) - **never in frontend** |
| `SUPABASE_RESUME_BUCKET` | Render | `resumes` |
| `SUPABASE_RECORDING_BUCKET` | Render | `recordings` |
| `OPENROUTER_API_KEY` | Render | your OpenRouter key - **never in frontend** |
| `OPENROUTER_ASSESSMENT_MODEL` | Render | `google/gemini-2.5-flash` (or your choice) |
| `OPENROUTER_TRANSCRIPTION_MODEL` | Render | `google/gemini-2.5-flash` (or your choice) |
| `AI_MONTHLY_BUDGET_USD` | Render | `20` |
| `AI_MAX_ASSESSMENT_CALLS_PER_MONTH` | Render | `500` (adjust to your expected volume) |
| `CORS_ORIGINS` | Render | `https://<your-username>.github.io` |
| `GITHUB_TOKEN` / `GITHUB_OWNER` / `GITHUB_REPO` / `GITHUB_BRANCH` / `GITHUB_DATA_PATH` | Render | same values you already use for the showcase |
| `VITE_API_BASE_URL` | GitHub Actions repo **variable** (not secret - it's a public URL) | your Render backend URL |

## G. Testing (end-to-end)

1. Open your GitHub Pages URL + `/#/apply`.
2. Submit a candidate application with 7.5+ years of experience.
3. Check the candidate appears in Supabase (Table Editor -> `candidates`) and, if configured, on your GitHub showcase site under "Application Review."
4. Continue to record 3 answers (audio or video) and submit.
5. Wait ~15-30 seconds for transcription + AI scoring (first request after idle may take longer - Render cold start).
6. Open `/#/recruiter`, log in, find the candidate.
7. Confirm the AI scorecard (per-competency scores, evidence, recommendation) is populated.
8. Click Shortlist -> confirm the showcase moves the candidate to "Screening."
9. Submit the recruiter scorecard -> confirm the showcase reflects the recruiter's decision and, if advancing, moves to "Take Home Test."
10. Check `GET /admin/ai-usage` (via a recruiter-authenticated request) to see the running monthly cost/call count.

## H. Local regression test (confirm nothing on your machine broke)

Your existing local setup requires zero changes. To confirm:
1. `cd backend`, activate your existing virtualenv, `pip install -r requirements.txt` (only adds two new cloud-only packages, safe either way).
2. Do **not** create/edit `backend/.env`'s `APP_MODE` line, or set it explicitly to `APP_MODE=local`.
3. `uvicorn app.main:app --reload --port 8000`, with Ollama running as before.
4. `cd frontend && npm install && npm run dev`.
5. Apply as a candidate, record answers, and check the recruiter dashboard exactly as you did before - the URLs are the same except routes now show a `#` (e.g. `http://localhost:5173/#/apply`) since HashRouter is used everywhere, including local dev.
6. Everything else - the 7.5-year bar, the 3-question flow, AI scoring via Ollama, the GitHub showcase push - is byte-for-byte the same code path as before.

---

## Open item needing your decision

Your brief describes two things that are in tension:
- Section 13/14 says the recruiter's screening notes/score should be visible on the public GitHub showcase (part of demonstrating "the complete recruitment journey").
- Section 15 says private recruiter notes should NOT be exposed on the public showcase unless you explicitly choose to.

I left this exactly as it was (recruiter notes/score ARE pushed to the showcase, as originally built) since section 13's description of the showcase's whole purpose depends on it, and recruiter screening notes are closer to "structured evaluation feedback" than to raw PII like email/phone/resume files (which I did remove). If you'd rather those notes stay private too, tell me and I'll strip `recruiter_notes`/`recruiter_score` from `_build_recruiter_report()` in `github_showcase_service.py` - it's a small, contained change.
