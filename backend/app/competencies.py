from app.schemas import CompetencyDefinition, CompetencyKey

"""
Role-specific competency sets. Each role gets 5 competencies drawn from
the 10 fixed CompetencyKey values (no schema changes needed) - labels
and prompts are tailored per role so scoring is actually relevant to
that job function.

Operability Engineer (DevOps) is kept exactly as it was before this
change - it's the role used in the live demo, already validated
against real production scenarios.

Business Analyst and Delivery Lead intentionally use a different set
of competency keys (focused_on_the_user, influence, collaboration,
educating) since "Automation"/"Technical Aptitude" don't meaningfully
describe what makes someone strong in those roles.
"""

ROLE_COMPETENCIES = {
    "operability-engineer": [
        CompetencyDefinition(
            key=CompetencyKey.breadth_of_knowledge,
            label="Breadth of Knowledge",
            prompt="Assess security judgment, networking implementation/troubleshooting, adaptability, learning from failure, resilience, operability, and observability."
        ),
        CompetencyDefinition(
            key=CompetencyKey.automation,
            label="Automation",
            prompt="Assess whether the candidate automates repeatable work, keeps solutions simple, understands cost implications, and values testing."
        ),
        CompetencyDefinition(
            key=CompetencyKey.technical_aptitude,
            label="Technical Aptitude",
            prompt="Assess full-stack awareness, ability to build maintainable services, tests, load balancers, CI/CD, cloud, containers, and developer peer discussion."
        ),
        CompetencyDefinition(
            key=CompetencyKey.continuous_delivery,
            label="Continuous Delivery",
            prompt="Assess small increments, production-first thinking, feature flags, canary deployments, and separation of deployment from release."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess clarity in verbal/written communication, explaining technical ideas to different audiences, and working with other teams/providers."
        ),
    ],
    "backend-engineer": [
        CompetencyDefinition(
            key=CompetencyKey.breadth_of_knowledge,
            label="Breadth of Knowledge",
            prompt="Assess understanding of data modeling, concurrency, caching, API design, and failure handling in backend systems."
        ),
        CompetencyDefinition(
            key=CompetencyKey.automation,
            label="Automation",
            prompt="Assess whether the candidate automates repeatable work like testing, migrations, and deployment tasks."
        ),
        CompetencyDefinition(
            key=CompetencyKey.technical_aptitude,
            label="Technical Aptitude",
            prompt="Assess ability to design scalable, maintainable services, databases, and APIs, and reason about trade-offs."
        ),
        CompetencyDefinition(
            key=CompetencyKey.continuous_delivery,
            label="Continuous Delivery",
            prompt="Assess safe, incremental shipping practices - feature flags, backward-compatible migrations, staged rollouts."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess clarity explaining technical trade-offs to other engineers and non-technical stakeholders."
        ),
    ],
    "genai-engineer": [
        CompetencyDefinition(
            key=CompetencyKey.breadth_of_knowledge,
            label="Breadth of Knowledge",
            prompt="Assess understanding of LLM fundamentals, evaluation methods, hallucination risks, and responsible AI practices."
        ),
        CompetencyDefinition(
            key=CompetencyKey.automation,
            label="Automation",
            prompt="Assess automation of evaluation pipelines, prompt regression testing, and monitoring for model drift."
        ),
        CompetencyDefinition(
            key=CompetencyKey.technical_aptitude,
            label="Technical Aptitude",
            prompt="Assess prompt engineering, RAG design, model selection trade-offs, and integration architecture."
        ),
        CompetencyDefinition(
            key=CompetencyKey.continuous_delivery,
            label="Continuous Delivery",
            prompt="Assess safe rollout practices for AI features - staged releases, guardrails, rollback plans for model changes."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess ability to explain AI capabilities, limitations, and risk trade-offs to non-technical stakeholders."
        ),
    ],
    "frontend-engineer": [
        CompetencyDefinition(
            key=CompetencyKey.breadth_of_knowledge,
            label="Breadth of Knowledge",
            prompt="Assess understanding of browser rendering, accessibility, performance, and cross-browser considerations."
        ),
        CompetencyDefinition(
            key=CompetencyKey.automation,
            label="Automation",
            prompt="Assess automated testing practices (unit, component, visual regression) and CI integration for frontend code."
        ),
        CompetencyDefinition(
            key=CompetencyKey.technical_aptitude,
            label="Technical Aptitude",
            prompt="Assess component architecture, state management decisions, and performance optimization skills."
        ),
        CompetencyDefinition(
            key=CompetencyKey.continuous_delivery,
            label="Continuous Delivery",
            prompt="Assess safe UI release practices - feature flags, progressive rollout, and rollback strategy for frontend changes."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess collaboration with design and product, and ability to explain UX/technical trade-offs clearly."
        ),
    ],
    "qa-engineer": [
        CompetencyDefinition(
            key=CompetencyKey.breadth_of_knowledge,
            label="Breadth of Knowledge",
            prompt="Assess understanding of test strategy, risk-based testing, and different testing methodologies."
        ),
        CompetencyDefinition(
            key=CompetencyKey.automation,
            label="Automation",
            prompt="Assess test automation framework design, maintainability of automated suites, and CI integration."
        ),
        CompetencyDefinition(
            key=CompetencyKey.technical_aptitude,
            label="Technical Aptitude",
            prompt="Assess ability to design effective test cases, identify edge cases, and debug root causes of failures."
        ),
        CompetencyDefinition(
            key=CompetencyKey.continuous_delivery,
            label="Continuous Delivery",
            prompt="Assess use of quality gates in CI/CD pipelines and balancing test coverage with delivery speed."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess clarity of defect reporting and collaboration with developers to resolve issues."
        ),
    ],
    "data-engineer": [
        CompetencyDefinition(
            key=CompetencyKey.breadth_of_knowledge,
            label="Breadth of Knowledge",
            prompt="Assess understanding of data modeling, warehousing concepts, data quality, and pipeline reliability."
        ),
        CompetencyDefinition(
            key=CompetencyKey.automation,
            label="Automation",
            prompt="Assess automation of data pipelines, orchestration, and data quality checks."
        ),
        CompetencyDefinition(
            key=CompetencyKey.technical_aptitude,
            label="Technical Aptitude",
            prompt="Assess pipeline design, schema evolution handling, and performance optimization for large datasets."
        ),
        CompetencyDefinition(
            key=CompetencyKey.continuous_delivery,
            label="Continuous Delivery",
            prompt="Assess safe deployment of pipeline changes without breaking downstream consumers."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess ability to explain data issues and trade-offs to non-technical data consumers."
        ),
    ],
    "mobile-android": [
        CompetencyDefinition(
            key=CompetencyKey.breadth_of_knowledge,
            label="Breadth of Knowledge",
            prompt="Assess understanding of Android app lifecycle, memory management, and platform fragmentation challenges."
        ),
        CompetencyDefinition(
            key=CompetencyKey.automation,
            label="Automation",
            prompt="Assess automated testing (unit, UI tests) and CI/CD practices for Android apps."
        ),
        CompetencyDefinition(
            key=CompetencyKey.technical_aptitude,
            label="Technical Aptitude",
            prompt="Assess architecture decisions, performance optimization, and handling of diverse device capabilities."
        ),
        CompetencyDefinition(
            key=CompetencyKey.continuous_delivery,
            label="Continuous Delivery",
            prompt="Assess staged rollout practices via Play Store tracks and safe release management."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess collaboration with design/backend teams and clarity explaining technical constraints."
        ),
    ],
    "mobile-ios": [
        CompetencyDefinition(
            key=CompetencyKey.breadth_of_knowledge,
            label="Breadth of Knowledge",
            prompt="Assess understanding of iOS app lifecycle, memory management, and Apple platform constraints."
        ),
        CompetencyDefinition(
            key=CompetencyKey.automation,
            label="Automation",
            prompt="Assess automated testing (XCTest, UI tests) and CI/CD practices for iOS apps."
        ),
        CompetencyDefinition(
            key=CompetencyKey.technical_aptitude,
            label="Technical Aptitude",
            prompt="Assess architecture decisions, performance optimization, and Swift/SwiftUI proficiency."
        ),
        CompetencyDefinition(
            key=CompetencyKey.continuous_delivery,
            label="Continuous Delivery",
            prompt="Assess safe release management through App Store review constraints and phased rollouts."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess collaboration with design/backend teams and clarity explaining technical constraints."
        ),
    ],
    "business-analyst": [
        CompetencyDefinition(
            key=CompetencyKey.breadth_of_knowledge,
            label="Business & Domain Knowledge",
            prompt="Assess understanding of business processes, requirements analysis techniques, and domain research skills."
        ),
        CompetencyDefinition(
            key=CompetencyKey.focused_on_the_user,
            label="User & Stakeholder Focus",
            prompt="Assess ability to uncover real user needs, distinguish stated wants from underlying problems."
        ),
        CompetencyDefinition(
            key=CompetencyKey.influence,
            label="Influence & Negotiation",
            prompt="Assess ability to align stakeholders with competing priorities and drive decisions without formal authority."
        ),
        CompetencyDefinition(
            key=CompetencyKey.collaboration,
            label="Collaboration",
            prompt="Assess ability to work effectively across business, product, and engineering teams."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess clarity in requirements documentation and presenting findings to varied audiences."
        ),
    ],
    "delivery-lead": [
        CompetencyDefinition(
            key=CompetencyKey.continuous_delivery,
            label="Delivery & Risk Management",
            prompt="Assess ability to manage delivery risk, dependencies, and keep a program of work on track."
        ),
        CompetencyDefinition(
            key=CompetencyKey.influence,
            label="Influence & Leadership",
            prompt="Assess ability to lead teams and influence outcomes without direct authority over team members."
        ),
        CompetencyDefinition(
            key=CompetencyKey.collaboration,
            label="Collaboration",
            prompt="Assess facilitation skills and ability to unblock cross-functional teams."
        ),
        CompetencyDefinition(
            key=CompetencyKey.educating,
            label="Coaching & Team Development",
            prompt="Assess ability to mentor and grow team members, and build team capability over time."
        ),
        CompetencyDefinition(
            key=CompetencyKey.communication,
            label="Communication",
            prompt="Assess clarity in status reporting, escalation, and stakeholder communication under pressure."
        ),
    ],
}


def get_competencies_for_role(role: str):
    from app.roles import DEFAULT_ROLE
    return ROLE_COMPETENCIES.get(role, ROLE_COMPETENCIES[DEFAULT_ROLE])


def get_assessment_plan_for_candidate(role: str, candidate_id: str):
    """Returns the exact 3 competencies this candidate's assessment
    covers: 2 technical ones (round-robin rotated) + 1 consulting
    question (role-agnostic). This is the SINGLE source of truth for
    "which competencies apply to this candidate" - both /questions
    (to generate the actual question text) and /analyze (to know what
    to score) call this same function, so they can never disagree.

    Round-robin mechanism: every role's competency set has exactly one
    "communication" entry (dropped here, since the new consulting
    question now covers that ground) and exactly 4 remaining
    competencies. Those 4 are treated as a fixed cycle in the order
    they're already defined in ROLE_COMPETENCIES; a deterministic hash
    of the candidate_id picks a starting point in that cycle, and the
    2 competencies at that position and the next one (wrapping around)
    are selected. This gives 4 possible pairs across many candidates
    (not all 6 mathematically possible pairs), and - like every other
    hash-based selection in this app - the same candidate always gets
    the same pair (no re-rolling on page refresh), while different
    candidates get an even spread across all 4 competencies over time.
    """
    import hashlib

    from app.schemas import CompetencyKey, CompetencyDefinition
    from app.consulting_questions import get_consulting_question_for_candidate

    all_competencies = get_competencies_for_role(role)
    technical_pool = [c for c in all_competencies if c.key != CompetencyKey.communication]

    if len(technical_pool) < 2:
        # Defensive fallback - should never happen given every role
        # currently has exactly 5 competencies including communication,
        # but if a future role is added without that shape, don't crash.
        selected_technical = technical_pool
    else:
        digest = hashlib.md5(f"{candidate_id}:{role}:rotation".encode()).hexdigest()
        start = int(digest, 16) % len(technical_pool)
        selected_technical = [
            technical_pool[start],
            technical_pool[(start + 1) % len(technical_pool)],
        ]

    consulting_category, _ = get_consulting_question_for_candidate(candidate_id)
    consulting_definition = CompetencyDefinition(
        key=CompetencyKey.consulting,
        label="Consulting Question",
        prompt=(
            f"This is a behavioral/consulting question (category: {consulting_category}), "
            "not a technical one. There is no reference answer to grade against. Assess "
            "clarity of communication, whether the candidate gives a real, specific example "
            "(not a vague generality), and whether they actually answered the question asked. "
            "The recruiter will independently watch or listen to this recording and form their "
            "own judgment - this score is a supporting signal only, not a verdict."
        ),
    )

    return selected_technical + [consulting_definition]


# Kept for any code that still imports the flat list directly - defaults
# to the DevOps set (the demo role) for backwards compatibility.
COMPETENCY_DEFINITIONS = ROLE_COMPETENCIES["operability-engineer"]