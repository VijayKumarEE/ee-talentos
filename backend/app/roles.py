"""
The 10 roles candidates can apply for. The `value` is what's stored on
the candidate record and drives which competency set + question bank
gets used - the `label` is just for display (dropdowns, emails, AI
prompts).
"""

ROLES = [
    {"value": "operability-engineer", "label": "Operability Engineer (DevOps)"},
    {"value": "backend-engineer", "label": "Backend Engineer"},
    {"value": "genai-engineer", "label": "Gen AI Engineer"},
    {"value": "frontend-engineer", "label": "Front End Engineer"},
    {"value": "qa-engineer", "label": "QA Engineer"},
    {"value": "data-engineer", "label": "Data Engineer"},
    {"value": "business-analyst", "label": "Business Analyst"},
    {"value": "delivery-lead", "label": "Delivery Lead"},
    {"value": "mobile-android", "label": "Mobile Developer - Android"},
    {"value": "mobile-ios", "label": "Mobile Developer - iOS"},
]

DEFAULT_ROLE = "operability-engineer"


def get_role_label(role_value: str) -> str:
    for r in ROLES:
        if r["value"] == role_value:
            return r["label"]
    return "the role"


def is_valid_role(role_value: str) -> bool:
    return any(r["value"] == role_value for r in ROLES)