"""
Static, curated content for the candidate-facing "about Equal Experts"
chatbot on the /apply page. Every fact here was pulled from
equalexperts.com directly (not generated) and confirmed by Vijay.

This is deliberately NOT auto-refreshed from the live site - Glassdoor
ratings and open roles change over time, and this MVP scope is a
periodically-updated snapshot, not a live feed. Update this file by
hand when facts go stale (see COMPANY_INFO_LAST_VERIFIED below).
"""

COMPANY_INFO_LAST_VERIFIED = "2026-08-23"

COMPANY_OVERVIEW = (
    "Equal Experts is a global technology consultancy, launched in 2007, "
    "with over 4,000 consultants across 5 continents. Unlike traditional "
    "consultancies, we're 100% owned by our own network (employees, "
    "consultants, and customers) and operate with a flat structure - no "
    "unnecessary hierarchy. Most of our people have 10+ years of "
    "experience, and we work with major clients like John Lewis, eBay, "
    "Klarna, Tesco Bank, and HMRC."
)
COMPANY_OVERVIEW_ICON = "\U0001F3E2"  # office building

LINKEDIN_URL = "https://www.linkedin.com/company/equal-experts/"

GLASSDOOR_URL = "https://www.glassdoor.co.uk/Reviews/Equal-Experts-Reviews-E517343.htm"
GLASSDOOR_ICON = "\U0001F3C6"  # trophy
GLASSDOOR_STAT = "Top 10"
GLASSDOOR_CAPTION = (
    "Best Place to Work in the UK on Glassdoor, 3 years running - 99% of "
    f"people recommend working there (as of {COMPANY_INFO_LAST_VERIFIED})."
)
# Kept as a single sentence for plain-text fallback (e.g. non-card
# clients, screen readers) - the card rendering uses GLASSDOOR_STAT +
# GLASSDOOR_CAPTION separately instead.
GLASSDOOR_BLURB = f"{GLASSDOOR_STAT}: {GLASSDOOR_CAPTION}"

VALUES_ICON = "\u2B50"  # star
VALUES = [
    "We deliver as teams of equals",
    "We have a passion for learning over knowing all the answers",
    "We prioritise outcomes over approach",
    "We seek customer success over our own short-term interests",
    "We narrow our focus but widen our context",
    "We bring step-by-step change",
]

# This mirrors the real interview process from equalexperts.com/join-us -
# genuinely useful to surface here since it explains WHY the candidate
# is going through this exact screening tool.
# This reflects the actual current process as confirmed by Vijay, not
# just the generic version from equalexperts.com/join-us - the take-home
# deliberately omits a time estimate since it's done offline in the
# candidate's own time, and the final round is described as hybrid since
# it's usually in-person for India-based roles but may move to Zoom for
# urgent hiring needs.
INTERVIEW_PROCESS = [
    "An initial conversation about your experience",
    "A take-home technical assignment for some roles, completed in your own time",
    "A 90-minute technical pairing session on Zoom - covering a code walkthrough, code refactoring, and technical discussion",
    "A consulting/culture-fit conversation - usually in person for India-based roles, though it may be conducted over Zoom for urgent hiring needs",
]

NETWORK_BENEFITS_ICON = "\U0001F91D"  # handshake
NETWORK_BENEFITS = [
    "A flat structure - no unnecessary hierarchy",
    "Priority access to new projects across the network",
    "An instant professional network via Slack (#tech-community, #deliver-ee, and more)",
    "Ongoing career support between contracts",
    "You stay part of the network for as long as you want, even between engagements",
]

CAREERS_PAGE_URL = "https://job-boards.greenhouse.io/equalexperts"

LIFE_AT_EE_URL = "https://www.equalexperts.com/blog/category/ee-life/"
TEAM_URL = "https://www.equalexperts.com/about-us/our-team/"
CASE_STUDIES_URL = "https://www.equalexperts.com/case-studies/"

# Used in the chatbot's fallback message for anything outside its
# known topics. Phone number still not provided - leaving that as
# None rather than guessed.
CONTACT_EMAIL = "connect.india@equalexperts.com"
CONTACT_PHONE = None

# Structured facts for the "surprise me" button - deliberately NOT
# routed through the LLM classifier, since there's no ambiguity to
# resolve here (it always means the same thing: pick one at random).
# `stat` is the bold headline number shown in the fact card; leave it
# None for facts that don't reduce to a clean number, and the card
# renders as icon + caption only instead.
FUN_FACTS = [
    {"icon": "\U0001F30D", "stat": "4,000+", "caption": "Consultants across 5 continents"},
    {"icon": "\U0001F91D", "stat": "100%", "caption": "Owned by our own network - not outside investors"},
    {"icon": "\U0001F393", "stat": "90%", "caption": "Of our people have 10+ years of experience"},
    {"icon": "\U0001F3C6", "stat": "Top 10", "caption": "Best Place to Work in the UK on Glassdoor, 3 years running"},
    {"icon": "\U0001F4BC", "stat": None, "caption": "We work with major brands like John Lewis, eBay, Klarna, Tesco Bank, and HMRC"},
    {"icon": "\U0001F9ED", "stat": None, "caption": "We operate with a flat structure - no unnecessary hierarchy"},
    {"icon": "\U0001F504", "stat": None, "caption": "Once you pass our interview process, you're part of the network for as long as you want - even between contracts"},
    {"icon": "\u2B50", "stat": None, "caption": "\"We deliver as teams of equals\" is our #1 value, and it shapes how every project actually runs"},
]

# One direct JD link per role, deliberately not labelled by location in
# any candidate-facing text - hiring for most roles spans multiple
# cities (Bangalore, Pune, Gurgaon, etc.) and the candidate already
# picks their own location earlier in the application form, so a
# location label here would be misleading rather than helpful.
#
# frontend-engineer is None on purpose - there is no active opening for
# that role right now. mobile-android and mobile-ios intentionally
# point to the same single posting, since Equal Experts currently hires
# for one combined Mobile Engineer role rather than separate
# platform-specific postings.
#
# These are real live links as of COMPANY_INFO_LAST_VERIFIED - Greenhouse
# postings do get taken down when a role is filled, so this needs a
# periodic manual check, not a "set and forget."
ROLE_JD_LINKS = {
    "operability-engineer": "https://job-boards.greenhouse.io/equalexperts/jobs/7328118002",
    "backend-engineer": "https://job-boards.greenhouse.io/equalexperts/jobs/6679433002",
    "genai-engineer": "https://job-boards.greenhouse.io/equalexperts/jobs/8538926002",
    "frontend-engineer": None,
    "qa-engineer": "https://job-boards.greenhouse.io/equalexperts/jobs/6869201002",
    "data-engineer": "https://job-boards.greenhouse.io/equalexperts/jobs/5823892002",
    "business-analyst": "https://job-boards.greenhouse.io/equalexperts/jobs/8634234002",
    "delivery-lead": "https://job-boards.greenhouse.io/equalexperts/jobs/8425346002",
    "mobile-android": "https://job-boards.greenhouse.io/equalexperts/jobs/8195055002",
    "mobile-ios": "https://job-boards.greenhouse.io/equalexperts/jobs/8195055002",
}