from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import candidates, assessments, scheduling, dashboard, auth, company_chat
from app.competencies import COMPETENCY_DEFINITIONS
from app.schemas import CompetencyDefinition
from app.roles import ROLES

app = FastAPI(title="AI Pre-Screening MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175",
    ],
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
    return {"status": "ok"}


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