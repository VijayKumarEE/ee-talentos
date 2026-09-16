"""
Fixed allowlist of recruiters for the MVP (4 recruiters, per buildathon
scope). This single list drives both:
- Login: only these emails can access the recruiter side of the tool
- Tracked links: /apply/{code} tags an applying candidate with the
  right recruiter, so each recruiter only sees/owns candidates who
  applied through their own link

The "slug" values (r1, r2, r3, r4) are deliberately opaque - candidates
never see who "owns" their application, only the recruiting team does,
via this backend mapping. This is intentional: attribution happens
silently for accountability, without candidates feeling a specific
individual is gatekeeping their candidacy.

Real production version would replace this with actual Equal Experts
SSO restricted to your Workspace domain - this is the fast MVP path.
"""

RECRUITERS = [
    {"email": "vijay.kumar@equalexperts.com", "name": "Vijay Kumar", "slug": "r1"},
    {"email": "prathap.reddy@equalexperts.com", "name": "Prathap Reddy", "slug": "r2"},
    {"email": "srinidhi.sriraman@equalexperts.com", "name": "Srinidhi Sriraman", "slug": "r3"},
    {"email": "dharshan.j@equalexperts.com", "name": "Dharshan J", "slug": "r4"},
]


def get_recruiter_by_email(email: str):
    if not email:
        return None
    email = email.strip().lower()
    for r in RECRUITERS:
        if r["email"].lower() == email:
            return r
    return None


def get_recruiter_by_slug(slug: str):
    if not slug:
        return None
    slug = slug.strip().lower()
    for r in RECRUITERS:
        if r["slug"].lower() == slug:
            return r
    return None