"""
Console-based "email" service for the buildathon MVP.

Instead of actually sending email (no SMTP/API keys needed for the demo),
this prints a nicely formatted email to the backend terminal and keeps an
in-memory log of everything "sent" so the frontend can optionally display
it too (see SENT_EMAILS).

To go live later: replace the body of `send_email` with a real call
(SMTP, SendGrid, Gmail API, etc.) - callers (scheduling.py) don't need to
change at all.
"""

from datetime import datetime
from typing import List, Dict

from app.config import EMAIL_FROM

# Simple in-memory log of everything "sent" this run, so the frontend can
# show a "sent emails" panel if useful for the demo.
SENT_EMAILS: List[Dict] = []


def send_email(to: str, subject: str, body: str) -> Dict:
    record = {
        "from": EMAIL_FROM,
        "to": to,
        "subject": subject,
        "body": body,
        "sent_at": datetime.now().isoformat(),
    }
    SENT_EMAILS.append(record)

    print("\n" + "=" * 70)
    print("MOCK EMAIL SENT")
    print("=" * 70)
    print(f"From:    {record['from']}")
    print(f"To:      {record['to']}")
    print(f"Subject: {record['subject']}")
    print("-" * 70)
    print(record["body"])
    print("=" * 70 + "\n")

    return record


def build_self_scheduling_email(
    candidate_name: str, round_label: str, slots: List[Dict]
) -> str:
    lines = [
        f"Hi {candidate_name},",
        "",
        f"Congratulations on progressing to the {round_label} round!",
        "Please pick a time that works for you from the options below:",
        "",
    ]
    for slot in slots[:8]:  # cap for readability
        lines.append(f"  [{slot['slot_id'][:8]}] {slot['label']}")

    lines += [
        "",
        "Reply with your preferred slot ID (or use the self-scheduling link"
        " in the candidate portal) to confirm your interview.",
        "",
        "Best of luck,",
        "The Hiring Team",
    ]
    return "\n".join(lines)


def build_booking_confirmation_email(
    candidate_name: str, round_label: str, slot: Dict
) -> str:
    return (
        f"Hi {candidate_name},\n\n"
        f"Your {round_label} interview is confirmed for:\n\n"
        f"  {slot['label']}\n\n"
        "You'll receive a calendar invite shortly. Good luck!\n\n"
        "Best,\nThe Hiring Team"
    )


def build_interview_confirmed_email(
    candidate_name: str, role: str, confirmed_time: str, zoom_link: str = ""
) -> str:
    """Sent when a recruiter picks a specific time out of the
    candidate's stated availability and confirms it. This is the one
    email in that flow - the candidate isn't asked to negotiate a slot
    over email, only told the final confirmed time and where to join."""
    role_phrase = f" for the {role} role" if role else ""
    link_line = (
        f"Join here: {zoom_link}\n\n" if zoom_link
        else "The meeting link will follow separately.\n\n"
    )
    return (
        f"Hi {candidate_name},\n\n"
        f"Thanks for sharing your availability{role_phrase}. Your screening "
        f"call is confirmed for:\n\n"
        f"  {confirmed_time}\n\n"
        f"{link_line}"
        "See you then!\n\n"
        "Best,\nThe Hiring Team"
    )


def build_rejection_email(candidate_name: str, role: str = "", reason: str = "") -> str:
    """Generic placeholder rejection template. Swap the body text here
    once real approved wording/reasons are provided - callers
    (scheduling.py) don't need to change."""
    reason_line = f"\n{reason}\n" if reason else ""
    role_phrase = f" for the {role} role" if role else ""

    return (
        f"Hi {candidate_name},\n\n"
        f"Thank you for taking the time to apply{role_phrase} and "
        f"for completing our pre-screening assessment.\n"
        f"{reason_line}"
        "\nAfter careful review, we won't be moving forward with your "
        "application at this time. We know this isn't the news you were "
        "hoping for, and we genuinely appreciate the effort you put into "
        "your application.\n\n"
        "We'll keep your profile on file and would welcome an application "
        "for future roles that may be a better fit.\n\n"
        "Best,\nThe Hiring Team"
    )


def build_recruiter_new_application_email(
    recruiter_name: str, candidate_name: str, role: str
) -> str:
    """Sent to a recruiter the moment a candidate applies through their
    tracked link - mirrors the 'new take-home test submitted' style
    notification pattern from Greenhouse."""
    return (
        f"Hi {recruiter_name},\n\n"
        f"{candidate_name} has just applied for {role} through "
        "your application link.\n\n"
        "Log in to EE TalentOS to review their application once they've "
        "completed the pre-screening assessment.\n\n"
        "Best,\nEE TalentOS"
    )


def build_recruiter_assessment_complete_email(
    recruiter_name: str, candidate_name: str, overall_score: float, recommendation: str
) -> str:
    """Sent to the assigned recruiter as soon as a candidate finishes
    their AI-scored assessment - the key 'come look at this' trigger."""
    return (
        f"Hi {recruiter_name},\n\n"
        f"{candidate_name} has completed their pre-screening assessment.\n\n"
        f"  Overall score: {overall_score} / 5\n"
        f"  AI recommendation: {recommendation.replace('_', ' ')}\n\n"
        "Log in to EE TalentOS to review their full scorecard and "
        "resume, then shortlist or reject.\n\n"
        "Best,\nEE TalentOS"
    )