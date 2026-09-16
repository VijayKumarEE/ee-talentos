from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, EmailStr


class CompetencyKey(str, Enum):
    breadth_of_knowledge = "breadth_of_knowledge"
    automation = "automation"
    focused_on_the_user = "focused_on_the_user"
    technical_aptitude = "technical_aptitude"
    continuous_delivery = "continuous_delivery"
    collaboration = "collaboration"
    influence = "influence"
    communication = "communication"
    community = "community"
    educating = "educating"
    consulting = "consulting"


class AssessmentStage(str, Enum):
    pre_screen = "pre_screen"
    recruiter_screen = "recruiter_screen"
    panel_screen = "panel_screen"


class Recommendation(str, Enum):
    strong_match = "strong_match"
    review = "review"
    reject = "reject"


class CandidateApply(BaseModel):
    job_id: str
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    current_location: Optional[str] = None
    preferred_location: Optional[str] = None
    years_of_experience: Optional[int] = None
    months_of_experience: Optional[int] = None
    current_organization: Optional[str] = None
    current_role: Optional[str] = None
    interviewed_last_6_months: Optional[bool] = None
    notice_period_days: Optional[int] = None
    expected_salary: Optional[str] = None
    current_salary: Optional[str] = None
    fixed_salary: Optional[str] = None
    variable_pay: Optional[str] = None
    availability_slots: Optional[List[str]] = None
    call_mode: Optional[str] = None
    recruiter_slug: Optional[str] = None
    role_applied_for: str = "operability-engineer"
    source_channel: Optional[str] = None
    assessment_mode: str = "text"


class AssessmentAnswer(BaseModel):
    question_id: str
    question: str
    answer_text: Optional[str] = None
    transcript_text: Optional[str] = None
    media_url: Optional[str] = None


class AssessmentSubmit(BaseModel):
    answers: List[AssessmentAnswer]


class RecruiterReview(BaseModel):
    shortlist: bool
    recruiter_notes: Optional[str] = None
    recruiter_score: Optional[float] = None


class SkillEvidence(BaseModel):
    positive: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)


class CompetencyScore(BaseModel):
    key: CompetencyKey
    label: str
    score: float = Field(ge=0, le=5)
    level: str
    evidence: SkillEvidence = Field(default_factory=SkillEvidence)
    summary: str = ""
    follow_up_questions: List[str] = Field(default_factory=list)


class CandidateAssessmentRequest(BaseModel):
    candidate_id: str
    job_id: str
    role: str
    stage: AssessmentStage = AssessmentStage.pre_screen
    answers: Dict[str, str] = Field(default_factory=dict)


class CandidateAssessmentResponse(BaseModel):
    candidate_id: str
    job_id: str
    role: str
    stage: AssessmentStage
    competencies: List[CompetencyScore]
    overall_score: float = Field(ge=0, le=5)
    recommendation: Recommendation
    notes: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompetencyDefinition(BaseModel):
    key: CompetencyKey
    label: str
    prompt: str

class AssessmentQuestion(BaseModel):
    question_id: str
    competency_key: CompetencyKey
    question: str


class AssessmentQuestionsRequest(BaseModel):
    candidate_id: str
    job_id: str
    role: str


class AssessmentQuestionsResponse(BaseModel):
    candidate_id: str
    job_id: str
    role: str
    questions: List[AssessmentQuestion]