from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.routers import candidates, assessments, scheduling, dashboard, auth, company_chat
from app.competencies import COMPETENCY_DEFINITIONS
from app.schemas import CompetencyDefinition
from app.roles import ROLES
from app.config import APP_MODE, IS_CLOUD_MODE, CORS_ORIGINS
from app.auth_dependency import get_current_recruiter

app = FastAPI(title="AI Pre-Screening MVP")

# LOCAL MODE: unchanged - only the local Vite dev server origins, exactly
# as before.
# CLOUD MODE: only the origins explicitly listed in CORS_ORIGINS (e.g.
# your GitHub Pages origin, "https://yourname.github.io") - never "*".
# If CORS_ORIGINS is empty in cloud mode, no cross-origin browser can
# call this API at all (fails safe, rather than falling back to "*").
if IS_CLOUD_MODE:
    allowed_origins = CORS_ORIGINS
    if not allowed_origins:
        print(
            "[main] WARNING: APP_MODE=cloud but CORS_ORIGINS is empty - "
            "no browser origin will be able to call this API until you "
            "set CORS_ORIGINS in backend/.env (e.g. your GitHub Pages URL)."
        )
else:
    allowed_origins = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidates.router)
app.include_router(assessments.router)
app.include_router(scheduling.router)
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(company_chat.router)


@app.get("/health")
def health():
    return {"status": "ok", "app_mode": APP_MODE}


@app.get("/competencies", response_model=list[CompetencyDefinition])
def list_competencies():
    return COMPETENCY_DEFINITIONS


@app.get("/roles")
def list_roles():
    return ROLES


@app.get("/recruiters")
def list_recruiters():
    from app.recruiters import RECRUITERS
    return [{"name": r["name"], "slug": r["slug"]} for r in RECRUITERS]


@app.get("/admin/ai-usage")
def ai_usage(_recruiter: dict = Depends(get_current_recruiter)):
    """Simple monthly OpenRouter usage report (cost + call counts), for
    recruiter-side visibility into cost control. Kept recruiter-only,
    same as any other internal/admin data."""
    from app.cost_guard import get_monthly_usage
    return get_monthly_usage()