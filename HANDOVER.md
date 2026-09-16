# EE TalentOS - Handover

Written: 2026-09-13
Author of this doc: Claude, based on the working session with Vijay Kumar

This is a from-scratch handover for whoever picks this project up next
(including a future version of Vijay, or a future chat session). It
covers what the project is, what's actually built and working, what
tools it depends on, and exactly how to get it running again.

---

## 1. What this project is

**EE TalentOS** is a buildathon MVP built by a recruiter (Vijay Kumar,
non-developer, using AI pair-programming) to demonstrate that
recruiters can build real internal tools with AI assistance - no
engineering team involved.

The core product: a candidate pre-screening tool for an Operability
Engineer (DevOps) role. A candidate applies, is auto-checked against a
minimum experience bar, and - if they pass - records themselves
answering a small set of technical + consulting competency questions.
Their recorded answers are transcribed and scored by a local AI model,
producing a structured scorecard (per-competency score, level,
evidence, follow-up questions, overall recommendation). A recruiter
then reviews that scorecard alongside the resume and makes real hiring
decisions through the tool.

Alongside that, there's a second piece built in this session: a
**public showcase** - a static site that mimics the look of Greenhouse
Recruiting (the real ATS many companies use), so leadership can see
what a "real" integration with an ATS would look like, without
actually paying for or integrating with Greenhouse. It's a stand-in /
proof-of-concept, not a real Greenhouse integration.

---

## 2. The three things in this zip

```
backend/     FastAPI Python backend - the actual TalentOS application
frontend/    React + TypeScript frontend - candidate + recruiter UI
showcase-site-source/   Static HTML/JS/CSS site - the Greenhouse-replica showcase
```

The showcase site's actual LIVE, hosted copy is separate from this zip
- it lives in its own GitHub repo (see section 5). The copy in this
zip is the source-of-truth template; the live one may have since
diverged slightly (real candidates pushed into its data.json).

---

## 3. Tools and tech stack (the "what are we actually using" list)

| Tool | What it's for | Where it's used |
|---|---|---|
| **Python 3.12** | Backend language | Entire `backend/` |
| **FastAPI** | Backend web framework | `backend/app/main.py` + all routers |
| **SQLAlchemy + SQLite** | Persistent storage (`mvp.db`, not included in this zip) | `backend/app/store.py` - a lightweight `SQLDict` wrapper, not a full ORM |
| **Ollama** (local LLM, model: `llama3.2:3b`) | Runs entirely on your machine, no API key/cost. Used for two things: (1) scoring the candidate's recorded competency answers into the AI scorecard, (2) extracting resume fields that need contextual understanding (current employer, title, location) | `backend/app/services/ollama_service.py`, `assessment_service.py`, `resume_parsing_service.py` |
| **faster-whisper** (model size: `base`, runs on CPU) | Transcribes the candidate's recorded audio/video answers into text before the AI scores them | `backend/app/services/transcription_service.py` |
| **pypdf** / **python-docx** | Extracts raw text out of uploaded resume PDFs/Word docs | `backend/app/services/resume_parsing_service.py` |
| **httpx** | Backend's HTTP client - used for both calling Ollama locally and pushing data to GitHub's API | Multiple services |
| **React + TypeScript + Vite** | Frontend framework/tooling | Entire `frontend/` |
| **GitHub Pages + GitHub REST API** | Hosts the public showcase site as static files; the backend pushes JSON updates to it via GitHub's Contents API (no real GitHub integration product - just using GitHub as free static hosting + a simple data store) | `backend/app/services/github_showcase_service.py`, `showcase-site-source/` |
| **Plain HTML/CSS/JS** (no framework) | The showcase site itself - deliberately dependency-free so it runs on GitHub Pages with zero build step | `showcase-site-source/` |

**Nothing here costs money or needs an external API key** except
GitHub (free) - Ollama and Whisper both run entirely locally on
Vijay's machine.

---

## 4. What's actually built and working right now

### Candidate-facing flow
- Apply form (name, email, phone, resume upload, experience)
- Resume upload auto-fills fields where possible (name/email/phone via
  pattern-matching, current employer/title/location via Ollama) -
  **just fixed this session**: phone number extraction was silently
  failing on the common Indian mobile format (`+91 XXXXX XXXXX`); now
  fixed and verified against 42 real uploaded resumes.
- Auto-reject if under 7.5 years of experience (candidate sees a
  generic "thank you," no specific reason shown to them)
- If passed: candidate records themselves answering competency
  questions (video/audio), submits
- Recording is transcribed (Whisper) then scored (Ollama) into a
  structured AI scorecard: per-competency score/level/evidence/
  follow-ups, overall score + recommendation (strong_match / review /
  reject)

### Recruiter-facing flow (dashboard)
- Recruiter sees the AI scorecard + resume for each candidate
- **Shortlist**: recruiter's first decision, based on the AI scorecard
  - available only when `stage == "assessed"`
  - sends a self-scheduling email for a recruiter screen call
- **Submit scorecard**: recruiter's second decision, after actually
  speaking with the candidate on that screen call
  - available only when `stage == "recruiter_scheduling_sent"`
  - if advancing: generates panel-round (technical + consulting
    interview) scheduling slots
  - if not: candidate is rejected
- **Buttons are now stage-gated** (fixed this session) - previously
  Shortlist/Reject/Submit-scorecard all showed unconditionally on
  every row regardless of what stage a candidate was actually in.

### The Greenhouse-replica showcase (built this session, in full)
A static site, hosted on GitHub Pages, styled to closely resemble
Greenhouse Recruiting's actual UI (candidate list + candidate detail
pages), scoped to just the Operability Engineer role for this MVP.

**Four real backend touchpoints push data into it automatically:**

1. `candidates.py -> apply_candidate()` - candidate applies -> lands
   on **Application Review**. If auto-rejected for experience, this is
   tagged Rejected immediately, with the specific reason shown (e.g.
   "Auto-rejected: 5.2 years of experience, below the 7.5 year
   minimum") - not just a generic "rejected" label.
2. `assessments.py -> analyze_candidate()` - once the AI finishes
   scoring, the **full AI report** (every competency's score, level,
   summary, strengths, gaps, follow-up questions - not just numbers)
   attaches to the Application Review stage. The candidate doesn't
   move yet - nothing recruiter-facing has happened.
3. `scheduling.py -> shortlist_candidate()` - recruiter clicks
   Shortlist -> candidate moves to **Screening**.
4. `scheduling.py -> submit_scorecard()` - recruiter's own notes/score
   from the actual screening call attach to the Screening stage
   (permanently - it doesn't get overwritten as the candidate moves
   further). If advancing, the candidate also moves to **Take Home
   Test**, which shows an automatic "Take-home assignment sent"
   status (the actual sending isn't built - this only reflects that
   the recruiter's decision to advance happened).

Each stage keeps its own permanent record once reached - exactly like
real Greenhouse, where you can scroll back through a candidate's
stage history and still see what happened at each step.

The push logic is deliberately **fire-and-forget**: if GitHub's API is
unreachable or misconfigured, it just prints a warning and the actual
candidate/recruiter flow continues unaffected. The showcase is a
mirror, not a dependency.

---

## 5. The live showcase site

**URL:** https://vijaykumaree.github.io/ee-talentos-showcase/

This is a **separate GitHub repo** from the main codebase, used purely
as free static hosting + a simple JSON data store (via GitHub's
Contents API). It is NOT part of this zip's folder structure - it's
its own repo, currently containing:
```
index.html
assets/app.js
assets/style.css
data/candidates.json   <- the live data, updated by the backend automatically
```
The `showcase-site-source/` folder in this zip is the template/source
copy - useful for reference or rebuilding, but the live site may have
since drifted (real candidates have been pushed into its
`data/candidates.json` that aren't reflected in this static copy).

**Backend config needed to talk to it** (`backend/.env`, not included
in this zip since it holds a real secret token):
```
GITHUB_TOKEN=ghp_...          (a GitHub Personal Access Token, repo scope)
GITHUB_OWNER=vijaykumaree
GITHUB_REPO=ee-talentos-showcase
GITHUB_BRANCH=main
GITHUB_DATA_PATH=data/candidates.json
```
If this file is missing or these values are blank, the showcase push
is silently skipped (see fire-and-forget note above) - the rest of the
app works fine either way.

---

## 6. How to get it running again

### Backend
```
cd backend
python3 -m venv .venv          # if not already created
source .venv/bin/activate
pip install -r requirements.txt
# create backend/.env with the GitHub values above (see section 5)
uvicorn app.main:app --reload --port 8000
```
Also needs **Ollama** running locally with the `llama3.2:3b` model
pulled (`ollama pull llama3.2:3b`, then `ollama serve` if not already
running as a background service). Without Ollama running, AI scoring
and resume field extraction will fail gracefully (candidate can still
apply, just without those two features).

**First run only**: faster-whisper downloads its `base` model
automatically on first transcription - this takes a minute, then it's
cached locally.

### Frontend
```
cd frontend
npm install
npm run dev
```

### Not included in this zip (lives only on Vijay's machine)
- `backend/mvp.db` - the actual SQLite database with real candidate
  data
- `backend/uploaded_resumes/` and `backend/uploaded_recordings/` -
  real uploaded files
- `backend/.env` - the real GitHub token

These were deliberately excluded from this handover zip since they're
runtime data/secrets, not "the build" - and some of the uploaded
resumes are real people's actual resumes used for testing, not
fictional test data.

---

## 7. Known limitations / things that are honestly not built yet

- The showcase only covers the **Operability Engineer** role - by
  design, for this MVP.
- The "Screening" stage in the showcase pipeline exists visually but
  has no real gating step before it in the actual app - shortlisting
  IS the moment that produces it (see section 4).
- There's no real Greenhouse integration - the showcase is a styled
  mimic, not a data sync with an actual Greenhouse account.
- Auto-rejected candidates never see their specific rejection reason
  (by design, to avoid disputes) - that reason is only visible
  internally, in the recruiter dashboard and the showcase.
- A few uploaded resumes (see backend service comments) genuinely have
  no phone number anywhere in the extracted text (not a bug - the
  document just doesn't contain one, sometimes because contact info is
  rendered as an image rather than real text).
