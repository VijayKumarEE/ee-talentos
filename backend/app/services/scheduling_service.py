"""
Mock scheduling logic for the buildathon MVP.

Generates fake-but-realistic available interview slots instead of calling
the real Google Calendar API. Each slot has a stable `slot_id` so the
candidate can "book" one by referencing that id.

Swapping this for real Google Calendar later just means replacing
`generate_mock_slots` with a call to the Calendar Freebusy API and mapping
the result into the same {slot_id, start, end, label} shape - nothing else
in the routers or frontend needs to change.
"""

from datetime import datetime, timedelta
from uuid import uuid4
from typing import List, Dict, Optional

from app.config import (
    SCHEDULING_DAYS_AHEAD,
    SLOTS_PER_DAY,
    SLOT_DURATION_MINUTES,
    BUSINESS_START_HOUR,
)


def _next_business_days(count: int) -> List[datetime]:
    days = []
    current = datetime.now() + timedelta(days=1)  # start from tomorrow
    while len(days) < count:
        if current.weekday() < 5:  # Mon-Fri
            days.append(current)
        current += timedelta(days=1)
    return days


def generate_mock_slots(panel: str = "recruiter") -> List[Dict]:
    """
    panel: "recruiter" or "panel" - purely a label so the email/UI can
    say which round these slots are for. Logic is identical either way.
    """
    slots = []
    business_days = _next_business_days(SCHEDULING_DAYS_AHEAD)

    for day in business_days:
        for i in range(SLOTS_PER_DAY):
            start = day.replace(
                hour=BUSINESS_START_HOUR + (i * 2), minute=0, second=0, microsecond=0
            )
            end = start + timedelta(minutes=SLOT_DURATION_MINUTES)

            slots.append(
                {
                    "slot_id": str(uuid4()),
                    "panel": panel,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "label": start.strftime("%A, %d %b - %I:%M %p"),
                }
            )

    return slots


def find_slot(slots: List[Dict], slot_id: str) -> Optional[Dict]:
    for slot in slots:
        if slot["slot_id"] == slot_id:
            return slot
    return None