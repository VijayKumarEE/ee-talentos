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

Source: the underlying 6 categories and intent were provided directly
by Vijay (screenshot of an internal document); the wording below has
been deliberately reworded per category (same intent, different
phrasing) so it doesn't read as identical to the internal consulting-
round questions - see chat history for the original wording and the
approved rewrite.
"""

import hashlib
from typing import Tuple

CONSULTING_QUESTIONS = [
    {
        "category": "Collaboration",
        "question": "Describe a time your team disagreed on the right approach - how did that play out?",
    },
    {
        "category": "Holistic Thinking",
        "question": "Walk me through a moment you had to quickly get up to speed on a complex situation before acting.",
    },
    {
        "category": "Adaptability",
        "question": "Tell me about a project where you weren't given clear instructions - what did you do?",
    },
    {
        "category": "Influence",
        "question": "Give an example of a time you pushed for a change and people pushed back - what happened?",
    },
    {
        "category": "Building Relationships",
        "question": "Describe working with someone on your team who wasn't fully engaged - how did you handle it?",
    },
    {
        "category": "Continuous Learning",
        "question": "Tell me about a time you had to pick up a tool or technology you'd never used before.",
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
