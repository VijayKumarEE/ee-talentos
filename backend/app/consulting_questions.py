"""
Role-agnostic consulting question bank.

Unlike the per-role technical question banks in question_bank.py, this
set is identical for every role - DevOps, Backend, Business Analyst,
all of them see one question drawn from the same 6 categories. This
question is NOT compared against a technical reference answer key.
The AI still evaluates it (clarity, whether a real example was given,
relevance to the actual question asked), but there's no "expert
answer" to grade against - the recruiter is expected to watch or
listen to the recording directly and form their own judgment of the
candidate's communication and articulation, using the AI's read as a
supporting signal only, not a verdict.

Source: provided directly by Vijay (screenshot of an internal
document), not derived from any external material.
"""

import hashlib
from typing import Tuple

CONSULTING_QUESTIONS = [
    {
        "category": "Collaboration",
        "question": "Tell me a specific time where you had to work in a team where there were conflicting opinions?",
    },
    {
        "category": "Holistic Thinking",
        "question": "Tell me about a specific time when you had to understand the big picture in a short amount of time?",
    },
    {
        "category": "Adaptability",
        "question": "Can you describe a specific situation where requirements were vague?",
    },
    {
        "category": "Influence",
        "question": "Tell me about a time when you met resistance when trying to introduce an improvement within your team.",
    },
    {
        "category": "Building Relationships",
        "question": "Tell me about a specific time when you had to work with a disengaged team member?",
    },
    {
        "category": "Continuous Learning",
        "question": "Give me a specific example of when you needed to work with an unfamiliar technology?",
    },
]


def get_consulting_question_for_candidate(candidate_id: str) -> Tuple[str, str]:
    """Deterministically picks one of the 6 consulting categories for
    this candidate - same hash-based approach as the technical question
    variants, so the same candidate always sees the same consulting
    question (no re-rolling on page refresh), but different candidates
    get a fair spread across all 6 categories. Returns (category, question)."""
    digest = hashlib.md5(f"{candidate_id}:consulting".encode()).hexdigest()
    idx = int(digest, 16) % len(CONSULTING_QUESTIONS)
    entry = CONSULTING_QUESTIONS[idx]
    return entry["category"], entry["question"]