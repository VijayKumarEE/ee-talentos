"""
Role-specific question bank with multiple variants per competency.
Variant selection is deterministic per-candidate (based on a hash of
their candidate_id) rather than a shared rotating counter - this
prevents candidates from sharing questions with each other and
pre-preparing answers, and unlike a counter-based approach, it's
completely immune to server restarts (which happen often during
development and would otherwise silently reset everyone back to the
same first variant).

Operability Engineer (DevOps) is the role used in the live demo and
was built from real production scenarios (DevOps_MVP_Doc) - its
reference knowledge is the most deeply validated. The other 9 roles
have functional, reasonable question sets that can be swapped for
better role-specific material later, the same way DevOps was upgraded
from generic placeholders to real scenarios.
"""

import hashlib
from typing import Dict, List

QUESTION_BANK: Dict[str, Dict[str, List[str]]] = {
    "operability-engineer": {
        "breadth_of_knowledge": [
            "During a deployment rollout, your ingress proxy starts throwing intermittent HTTP 502 and 503 errors, even though pod CPU and memory look healthy. Walk me through how you'd diagnose this, and what's actually happening under the hood.",
            "Your monitoring shows a spike in 5xx errors right after a rolling update, but only for about 30 seconds each time. What would you check first, and what's your hypothesis for the root cause?",
            "A teammate says 'just restart the pods' whenever they see 502s during deploys. What would you tell them about why that's treating the symptom, not the cause?",
            "You get paged for HTTP 502s that only happen during deploys, never at steady state. Walk me through how you'd narrow down whether it's a proxy timeout issue, a readiness probe issue, or something else.",
            "Explain, in your own words, why a TCP keep-alive mismatch between a proxy and an application can cause intermittent errors that look random but actually have a predictable pattern.",
            "When you create a Kubernetes Service of type LoadBalancer, walk me through exactly what happens end-to-end - what actually gets created on the cloud side, and how does a real user's request end up at a specific pod?",
            "Walk me through a single request to api.company.com from the moment DNS resolves it to the moment a pod actually handles it. Name every hop you can think of, including where TLS would terminate.",
            "A worker node suddenly goes NotReady in production. What actually happens to the pods that were running on it, and what would make that recovery fail or stall?",
            "What would you actually put on a dashboard for a production service, and why can 'all our infrastructure metrics are green' still be true while customers are experiencing failures?",
        ],
        "automation": [
            "You need to containerize a Python service for a banking client with a zero-vulnerability, immutable deployment requirement. Walk me through how you'd build and harden that Docker image, and why each step matters.",
            "A teammate wants to skip multi-stage Docker builds to save time on a deadline. What would you tell them about the trade-offs, and what's the minimum you wouldn't compromise on?",
            "How would you explain the difference between pinning a base image by tag versus by SHA256 digest to someone who thinks tags are 'good enough'?",
            "You're reviewing a Dockerfile that runs the app as root and copies the entire build toolchain into the final image. What would you flag, and how would you fix each issue?",
            "Why does using an exact digest instead of a mutable tag matter for supply-chain security, and what's a concrete scenario where a mutable tag caused real harm?",
            "Two engineers run `terraform apply` against the same production environment at almost the same time. What's supposed to stop that from corrupting your infrastructure state, and what would you tell a team that isn't already doing it?",
            "A `terraform apply` fails halfway through - some resources were created, others weren't. What's your first move, and why is 'just run terraform destroy and start over' usually the wrong instinct?",
            "Walk me through a CI/CD pipeline you've actually built or maintained, end to end - from a commit landing to that code running in production. What gate would you never remove, even under deadline pressure?",
            "How would you get a database password or an API token into a running container without ever putting it in a Git repo or a plain Kubernetes Secret? Walk me through what actually retrieves it and when.",
        ],
        "technical_aptitude": [
            "A pod is stuck in `Terminating` for over 30 minutes after you run `kubectl delete pod`. What are the likely causes, how would you safely diagnose it, and what would make you avoid a force delete?",
            "You notice several pods across your cluster are stuck in `Terminating` after a storage provider outage. Where would you start looking, and what's your safe recovery path?",
            "Why is `kubectl delete pod --force --grace-period=0` dangerous on a stateful workload, even when the pod looks stuck?",
            "A stateful pod won't finish terminating and a teammate suggests force-deleting it to 'unblock the deploy.' Walk me through what could go wrong if you do that, and what you'd check first instead.",
            "Explain what a Kubernetes finalizer is, and how an orphaned finalizer from a crashed operator could leave a pod stuck in Terminating indefinitely.",
            "Only about 10% of requests are failing with a 5xx, not all of them. Before you touch anything, how would you figure out whether that 10% is hitting the same backend, the same region, or something else entirely?",
            "Explain where TLS actually terminates in an architecture you've worked with, and then walk me through how you'd rotate that certificate in production without causing a single failed handshake.",
            "A container image runs perfectly on a developer's laptop and then fails as soon as it's deployed to production. Give me three genuinely different root causes for that, not just 'it's a config issue.'",
            "Tell me about a real production issue where your first hypothesis turned out to be wrong. What made you initially think that, what evidence changed your mind, and what was actually going on?",
            "What's the most technically challenging production problem you've personally solved? I want the real architecture, the actual symptoms, what you tried that didn't work, and what finally fixed it.",
        ],
        "continuous_delivery": [
            "Your team wants to stop developers from accidentally deploying insecure configurations - like mutable `:latest` tags or privileged root containers - straight into production. How would you build that guardrail into the deployment pipeline?",
            "A developer argues code review alone should be enough to prevent bad configs reaching production. How would you make the case for automated policy enforcement instead?",
            "How would you roll out a new admission-control policy without breaking existing deployments on day one?",
            "You've just introduced a Kyverno policy that blocks privileged containers, but several existing workloads violate it. Walk me through how you'd roll this out without breaking them on day one.",
            "What's the difference between catching a bad Kubernetes config in code review versus blocking it at the cluster level with policy-as-code, and why does that difference matter at scale?",
            "Kubernetes reports a deployment as fully successful and healthy. Give me a real scenario where that's true and the application is still completely broken for users - and how your rollout process would have caught it.",
            "Compare rolling updates, blue-green, and canary deployments for a high-risk production change. Which would you actually pick, and what would make you choose differently?",
            "You're about to ship a change you genuinely consider risky. Walk me through the actual steps you'd take before, during, and after the deploy - not the theory, what you'd literally do.",
            "After you've made a fix, how do you actually know it worked - not just that the deploy succeeded, but that the original problem is gone? Give me a concrete example of how you validated a fix.",
        ],
        "communication": [
            "Describe a time you had to explain a complex technical issue (like an outage or a security risk) to a non-technical stakeholder. How did you frame it, and how did that shape what happened next?",
            "How would you explain a production incident's root cause to a product manager who just wants to know 'is it fixed and will it happen again'?",
            "Tell me about a time you had to push back on a leadership decision for technical reasons. How did you make your case?",
            "A stakeholder asks 'why can't we just fix it faster' after a major outage. How would you explain the real trade-offs without sounding defensive?",
            "Describe how you'd communicate a security vulnerability finding to a non-technical executive who needs to decide whether to delay a release.",
            "How would you explain a production incident to a non-technical stakeholder who wants to know what happened, without using words like 'pod,' 'ingress,' or 'connection pool'? Give me a real example.",
            "You're asked a question in an interview or a meeting about a technology you genuinely haven't used in production. What do you actually say, versus what a lot of people are tempted to say?",
            "How would you explain the difference between a symptom and a root cause to someone outside your team who just wants the postmortem in plain language?",
            "Walk me through how you'd both handle and communicate a live production outage - what you're doing technically at each stage, and what you're telling stakeholders at that same stage.",
        ],
    },
    "backend-engineer": {
        "breadth_of_knowledge": [
            "You're seeing intermittent timeouts on a database query that normally runs fast. Walk me through how you'd narrow down whether it's a locking issue, an index problem, or connection pool exhaustion.",
            "A service that was fine at 100 requests/second starts failing at 500. What are the first three things you'd check?",
            "How would you explain the trade-offs between strong consistency and eventual consistency to a product owner pushing for 'just make it always correct'?",
            "Why might you choose immutable domain objects with validation in the constructor over plain mutable classes with setters?",
            "A getter on your domain model exposes an internal collection, like a List. What's your approach, and why?",
            "When would you introduce a dedicated status or state model - an enum or small value object - rather than tracking state with booleans or scattered flags?",
            "How do you decide whether a piece of mutable state, like a quantity or running total, belongs on a child item versus being managed by the parent that holds it?",
            "What's your view on representing a domain concept using raw primitives or generic maps versus a dedicated class or value object?",
            "Why would you use a fixed-point or decimal type instead of double or float for currency calculations?",
            "How do you ensure rounding behaviour is applied consistently for money calculations across a codebase?",
            "How would you validate a numeric input like a quantity to protect the system from an invalid business state, such as negative or zero where that isn't allowed?",
            "When the same item can be added multiple times and quantities need to be combined, what approach would you use to merge them cleanly?",
            "What pitfalls should you be aware of when comparing two BigDecimal values for equality in code or in a test?",
        ],
        "automation": [
            "Describe a manual database migration process your team used to run by hand that you automated. What could go wrong with the manual version, and how did automation reduce that risk?",
            "How would you automate rollback for a database migration that partially failed halfway through?",
            "A teammate wants to skip writing tests for a 'quick' API change. How do you respond?",
            "Walk through what a genuine red-green-refactor TDD loop looks like to you, in your own words.",
            "How do you decide the boundary between a unit test and an integration test, especially for code that calls an external service?",
            "What's the difference between a mock and a spy in unit testing, and when would you reach for each?",
            "You're adding a new validation rule to existing code. Do you write the test first or the implementation first, and why?",
            "How would you assert that two custom domain objects are equal in a test, when equality needs to be based on business meaning, like two money amounts that are numerically equal but represented differently?",
            "Describe the key stages of a CD pipeline from a code commit to it running in production.",
            "What's the difference between checks that should be automated in a pipeline versus ones that should remain manual, and why?",
            "How do feature flags or toggles support safer releases, and what would you consider before relying on one for a production deployment?",
            "What branching strategy would you use to keep a codebase always in a deployable state, and why?",
            "What quality gates or approvals would you expect a change to pass through before it's considered ready for release?",
        ],
        "technical_aptitude": [
            "Design a rate-limiting strategy for a public API that's being hit by both legitimate high-volume customers and abusive traffic. What trade-offs would you make?",
            "You need to add a new required field to an API response without breaking existing clients. Walk me through your approach.",
            "How would you decide between a message queue and a direct synchronous API call for two services that need to communicate?",
            "How do you decide when a class has taken on too many responsibilities and should be split?",
            "Why might you introduce an interface for a client that calls an external API, rather than depending on the concrete client class directly?",
            "When would you choose composition over inheritance when designing two related classes?",
            "You need to add a new business rule to an existing pricing or calculation flow without breaking the tests that already pass. How do you approach it?",
            "How would you explain the difference between tight and loose coupling, and how would you reduce coupling in a class that both talks to an external dependency and performs its own calculations?",
            "Think of a real system you've worked on. How would you go about identifying its pain points and deciding how to address them?",
            "When choosing a framework or technology for a component, what factors do you weigh, and can you give a real example?",
            "What security concerns would you evaluate when designing a feature that integrates with an external API or third-party service?",
            "How would you reason about performance and scaling concerns for a service that suddenly needs to handle significantly more load?",
            "How does working with microservices or event-driven architecture change your approach to testing and error handling compared to a single monolithic application?",
        ],
        "continuous_delivery": [
            "You need to change a core data model that several other services depend on. How would you roll this out without a big-bang cutover?",
            "How would you use feature flags to safely test a risky backend change with a small percentage of production traffic first?",
            "A migration needs to run against a live production database with zero downtime. What's your plan?",
            "You have a service class that both orchestrates business logic and directly calls an external API. How would you separate these concerns?",
            "How do you recognise when a 'service' class is doing too much, and how would you split it?",
            "How would you decide whether calculation logic, like a tax or fee calculation, belongs on a domain model itself or in a separate service or policy class?",
            "What signals tell you that an abstraction, like an extra service, wrapper class, or layer, is trivial and adding no real value?",
            "How would you design a component so that it can be tested in isolation without making a real network call?",
            "What observability signals - metrics, logs, traces - would you want in place for a service running in production, and why does each matter?",
            "How would you approach vulnerability scanning as part of the delivery process, and what would you do when a scan flags an issue?",
            "How do you approach authentication and authorization when designing a service, and can you explain the difference between them?",
            "Walk through how you'd detect and respond to an incident in a production service, like a spike in errors or latency.",
            "How do you know you're building the right thing, beyond just shipping working code? What feedback loops matter to you?",
        ],
        "communication": [
            "How would you explain a backward-incompatible API change to downstream teams who depend on your service, well before you ship it?",
            "Describe a time you had to tell a stakeholder that a requested feature would take much longer than they expected. How did that conversation go?",
            "How do you communicate a production incident's impact and timeline to non-engineers while it's still ongoing?",
            "How would you design exception types for a client that calls an external API and can fail in several distinct ways, like not found, invalid input, or service unavailable?",
            "When would you wrap a lower-level exception in a new, higher-level exception versus letting it propagate directly?",
            "How do you decide between using a checked exception versus an unchecked runtime exception for a given failure case?",
            "How would you handle the case where an external service responds that a requested resource, like a specific record or product, doesn't exist?",
            "How should error handling differ between a reusable library or client class and the application code that calls it?",
            "How do you use AI coding assistants in your day-to-day development, while making sure engineering quality doesn't slip?",
            "What are the risks of over-relying on AI-generated suggestions during development, and how would you mitigate them?",
            "If a product could 'easily switch' between different AI model providers to manage cost, what technical nuance would you raise?",
            "During a pairing session, how do you communicate your design trade-offs to your partner while you're actively writing code?",
            "How do you respond when a pairing partner or reviewer suggests a different approach than the one you've already started implementing?",
        ],
    },
    "genai-engineer": {
        "breadth_of_knowledge": [
            "A chatbot you built confidently gives an incorrect answer to a user. Walk me through how you'd investigate whether this is a hallucination, a retrieval failure, or a prompt issue.",
            "What are the main risks of shipping an LLM feature without an evaluation framework, and how would you explain those risks to a product manager?",
            "How would you decide whether a use case actually needs an LLM versus a simpler rules-based or classical ML approach?",
        ],
        "automation": [
            "How would you build an automated evaluation pipeline to catch regressions every time you change a prompt or swap models?",
            "A teammate wants to manually spot-check LLM outputs before each release instead of building automated evals. What would you tell them?",
            "How would you automate detection of PII leakage in LLM outputs before they reach a customer?",
        ],
        "technical_aptitude": [
            "Design a RAG (retrieval-augmented generation) system for a customer support use case. What are the key failure modes you'd design around?",
            "How would you reduce hallucination rates in a customer-facing LLM feature without simply making the model overly cautious and unhelpful?",
            "Walk me through how you'd choose between a larger, slower model and a smaller, faster one for a latency-sensitive production feature.",
        ],
        "continuous_delivery": [
            "How would you safely roll out a new model version to production without risking a regression in output quality for all users at once?",
            "What guardrails would you put in place before allowing an LLM feature to take real-world actions (like sending emails or making purchases) autonomously?",
            "How would you design a rollback plan for a prompt change that turns out to perform worse in production than in testing?",
        ],
        "communication": [
            "How would you explain to a non-technical stakeholder why an LLM feature can't be guaranteed to be 100% accurate, without undermining their confidence in shipping it?",
            "Describe how you'd communicate the cost trade-offs of using a more capable (and more expensive) model versus a cheaper one.",
            "How would you explain a hallucination incident to a customer-facing team who wants a simple explanation of what went wrong?",
        ],
    },
    "frontend-engineer": {
        "breadth_of_knowledge": [
            "A page performs fine on your dev machine but feels sluggish for real users. What are the first things you'd investigate?",
            "How would you explain the accessibility risks of a custom dropdown component built without proper ARIA attributes?",
            "A component re-renders far more often than expected. Walk me through how you'd diagnose why.",
        ],
        "automation": [
            "How would you set up automated visual regression testing to catch unintended UI changes before they reach production?",
            "A teammate wants to skip writing component tests to move faster. How do you respond?",
            "How would you automate accessibility checks as part of your CI pipeline?",
        ],
        "technical_aptitude": [
            "Design a state management approach for a complex form with interdependent fields and async validation. What trade-offs would you consider?",
            "How would you architect a component library to be reused consistently across multiple product teams?",
            "A page needs to load large datasets without freezing the UI. What approaches would you consider?",
        ],
        "continuous_delivery": [
            "How would you use feature flags to safely test a risky UI redesign with a subset of users first?",
            "A new frontend release causes a spike in errors for a specific browser. How would you have caught this before full rollout?",
            "How would you roll back a bad frontend deployment with minimal user impact?",
        ],
        "communication": [
            "Describe a time a designer's vision wasn't technically feasible as specified. How did you navigate that conversation?",
            "How would you explain a performance trade-off to a product manager who just wants 'more features, faster'?",
            "How do you communicate scope changes to a team mid-sprint when a UI requirement turns out to be more complex than expected?",
        ],
    },
    "qa-engineer": {
        "breadth_of_knowledge": [
            "How would you decide what to test manually versus what to automate for a new feature under a tight deadline?",
            "A bug slips into production despite passing all automated tests. How would you investigate the gap in coverage?",
            "How would you approach testing a feature that behaves differently depending on user permissions or roles?",
        ],
        "automation": [
            "Your automated test suite has become slow and flaky, and developers are starting to ignore failures. How would you fix this?",
            "How would you decide which tests belong in a fast unit suite versus a slower end-to-end suite?",
            "A teammate wants to automate everything, including one-off exploratory tests. How do you respond?",
        ],
        "technical_aptitude": [
            "Design a test strategy for a payment feature where failures have real financial consequences.",
            "How would you approach testing an API that depends on a third-party service with its own rate limits?",
            "A feature has many edge cases around date/timezone handling. How would you structure test coverage for it?",
        ],
        "continuous_delivery": [
            "How would you design quality gates in a CI/CD pipeline that catch real issues without slowing down every deploy?",
            "A release is under pressure to ship despite some tests failing. How do you handle that conversation?",
            "How would you balance thorough regression testing against a team's push for faster release cycles?",
        ],
        "communication": [
            "Describe how you'd write a bug report that gets a developer to understand and fix the issue quickly, without back-and-forth.",
            "How would you push back on a developer who dismisses a bug as 'not a real issue'?",
            "How do you communicate testing risk to a product manager who wants to ship despite known gaps in coverage?",
        ],
    },
    "data-engineer": {
        "breadth_of_knowledge": [
            "A nightly data pipeline that used to finish in 20 minutes now takes 3 hours. What would you investigate first?",
            "How would you explain the trade-offs between a data warehouse and a data lake to a stakeholder deciding which to invest in?",
            "A downstream report shows numbers that don't match the source system. How would you trace where the discrepancy was introduced?",
        ],
        "automation": [
            "How would you automate data quality checks so bad data is caught before it reaches a dashboard executives rely on?",
            "A teammate manually re-runs failed pipeline jobs each morning. How would you automate that safely?",
            "How would you automate schema-change detection so pipelines don't silently break when an upstream source changes?",
        ],
        "technical_aptitude": [
            "Design a pipeline that needs to handle both historical backfills and ongoing incremental loads. What trade-offs would you consider?",
            "How would you handle a slowly-changing dimension in a data warehouse when historical accuracy matters?",
            "A pipeline processes data in the wrong order due to out-of-order event arrival. How would you redesign it to handle that?",
        ],
        "continuous_delivery": [
            "How would you deploy a breaking schema change to a pipeline without disrupting downstream consumers who depend on the old format?",
            "What's your rollback plan if a new pipeline version produces subtly incorrect data that isn't caught immediately?",
            "How would you safely test a pipeline change against production-scale data before fully deploying it?",
        ],
        "communication": [
            "How would you explain a data quality issue's business impact to a non-technical stakeholder relying on that data for decisions?",
            "Describe a time you had to tell a stakeholder that requested data simply wasn't reliable enough to use as-is.",
            "How do you communicate the trade-off between data freshness and pipeline cost to someone who just wants 'real-time everything'?",
        ],
    },
    "mobile-android": {
        "breadth_of_knowledge": [
            "An app works fine on your test device but crashes on older, lower-memory Android devices. How would you investigate?",
            "How would you explain the impact of Android's fragmented device/OS landscape on your testing strategy?",
            "A feature drains battery unusually fast in the background. What would you check first?",
        ],
        "automation": [
            "How would you set up automated UI testing that runs reliably across multiple Android device configurations?",
            "A teammate wants to skip automated tests for a 'small' UI change. How do you respond?",
            "How would you automate crash reporting triage so your team catches regressions quickly after release?",
        ],
        "technical_aptitude": [
            "Design an offline-first architecture for a feature that needs to work with unreliable connectivity.",
            "How would you architect a large Android app to keep build times and modularity manageable as the team grows?",
            "A screen has janky scrolling performance. Walk me through how you'd diagnose and fix it.",
        ],
        "continuous_delivery": [
            "How would you use staged rollouts on the Play Store to catch a bad release before it reaches all users?",
            "What's your plan if a released app version has a critical bug affecting a subset of users?",
            "How would you test a risky change against production traffic patterns before a full release?",
        ],
        "communication": [
            "How would you explain a platform limitation (like background processing restrictions) to a product manager who wants a feature that conflicts with it?",
            "Describe how you'd collaborate with a backend team when an API contract needs to change to support a new mobile feature.",
            "How do you communicate a scope/timeline risk when a 'simple' UI request turns out to require significant native work?",
        ],
    },
    "mobile-ios": {
        "breadth_of_knowledge": [
            "An app passes App Store review but crashes for a subset of users in production. How would you investigate?",
            "How would you explain the trade-offs of supporting older iOS versions to a product manager who wants the latest APIs?",
            "A feature works in the simulator but not on physical devices. What would you check first?",
        ],
        "automation": [
            "How would you set up automated UI testing that's reliable across different iPhone screen sizes?",
            "A teammate wants to skip writing XCTest coverage for a 'simple' feature. How do you respond?",
            "How would you automate crash/crash-log triage to catch regressions quickly after a release?",
        ],
        "technical_aptitude": [
            "Design an offline-first architecture for a feature that needs to work with unreliable connectivity.",
            "How would you structure a large iOS codebase using SwiftUI to keep it maintainable as the team scales?",
            "A screen has janky scrolling performance. Walk me through how you'd diagnose and fix it.",
        ],
        "continuous_delivery": [
            "How would you use phased release on the App Store to catch a bad release before it reaches all users?",
            "App Store review can take days - how does that change your approach to releasing a critical fix quickly?",
            "How would you test a risky change safely, given you can't easily do a fast rollback once Apple approves a release?",
        ],
        "communication": [
            "How would you explain an Apple platform restriction to a product manager who wants a feature that conflicts with it?",
            "Describe how you'd collaborate with a backend team when an API contract needs to change to support a new iOS feature.",
            "How do you communicate a scope/timeline risk when App Store review adds unpredictable delay to a release plan?",
        ],
    },
    "business-analyst": {
        "breadth_of_knowledge": [
            "How would you approach understanding a business process you've never worked with before, before writing any requirements?",
            "A stakeholder gives you a solution ('build me a dashboard') instead of a problem. How do you get to the actual underlying need?",
            "How would you research and validate an assumption about how users currently work before proposing a change?",
        ],
        "focused_on_the_user": [
            "Two user groups want conflicting things from the same feature. How would you uncover what each group actually needs underneath their stated request?",
            "How would you validate that a proposed solution actually solves the problem, before it goes to development?",
            "Describe how you'd gather requirements from a stakeholder who struggles to articulate what they want.",
        ],
        "influence": [
            "Two senior stakeholders disagree on priority for the same sprint. How would you help them reach a decision?",
            "How would you push back on a stakeholder who wants to add scope after requirements are already signed off?",
            "Describe a time you had to convince a team to change direction based on evidence they initially resisted.",
        ],
        "collaboration": [
            "How would you work with both engineering and business stakeholders who have very different vocabularies and priorities?",
            "Describe how you'd handle a disagreement between product and engineering about feasibility of a requirement.",
            "How would you ensure requirements stay accurate as a project evolves and multiple people are updating them?",
        ],
        "communication": [
            "How would you write a requirements document that's clear enough for engineers but still readable by business stakeholders?",
            "Describe how you'd present a complex set of trade-offs to leadership in a way that leads to a clear decision.",
            "How would you communicate that a requested feature isn't feasible in the current timeline, without shutting down the conversation?",
        ],
    },
    "delivery-lead": {
        "continuous_delivery": [
            "A project is falling behind schedule due to an unresolved external dependency. How would you manage that risk?",
            "How would you decide whether to cut scope or push a deadline when a project is at risk of missing both?",
            "Describe how you'd track and communicate delivery risk across multiple workstreams running in parallel.",
        ],
        "influence": [
            "How would you get a team to commit to a delivery plan when you don't have direct authority over them?",
            "A senior stakeholder wants an unrealistic deadline. How would you negotiate a more realistic one without damaging the relationship?",
            "Describe a time you had to influence a decision where you had no formal authority over the outcome.",
        ],
        "collaboration": [
            "How would you unblock two teams who are stuck waiting on each other for a shared dependency?",
            "Describe how you'd facilitate a disagreement between a product owner and a tech lead about priorities.",
            "How would you keep a distributed team aligned when working across different time zones?",
        ],
        "educating": [
            "How would you help a junior team member grow into taking more ownership of delivery decisions?",
            "Describe how you'd coach a struggling team member without undermining their confidence.",
            "How would you build delivery-management capability across a team so it doesn't all depend on you?",
        ],
        "communication": [
            "How would you communicate a serious delivery risk to leadership before it becomes a crisis?",
            "Describe how you'd handle a status update when the honest answer is 'we're behind and I'm not sure we'll recover.'",
            "How would you keep stakeholders informed without overwhelming them with unnecessary detail?",
        ],
    },
}


REFERENCE_KNOWLEDGE: Dict[str, Dict[str, str]] = {
    "operability-engineer": {
        "breadth_of_knowledge": (
            "Core mechanics: HTTP 503 (No Healthy Upstream) happens when the "
            "ingress controller sees an empty Endpoints/EndpointSlices list, "
            "typically because rolling updates terminate old pods faster "
            "than new pods clear their readiness probes. HTTP 502 happens "
            "from a TCP reset / idle keep-alive race: the proxy's keep-alive "
            "timeout outlives the backend app's, so the proxy sends a "
            "request down a socket the app already closed. A Kubernetes "
            "Service of type LoadBalancer is not itself the load balancer - "
            "the cloud-provider integration translates it into real "
            "cloud-side infrastructure (an ALB/NLB, Azure LB, etc); "
            "troubleshooting means checking both the Kubernetes "
            "Service/Endpoints/pod-readiness side AND the cloud networking "
            "side. A full request path is DNS -> external LB/ingress "
            "endpoint -> ingress/router evaluates host+path -> Kubernetes "
            "Service -> Endpoints (ready pods only) -> pod. When a node "
            "goes NotReady, Kubernetes eventually reschedules its pods "
            "elsewhere, but only if the cluster has spare capacity - node "
            "failure can expose a capacity-planning gap, not just a "
            "scheduling one. Golden signals (latency, traffic, errors, "
            "saturation) plus pod/node health are necessary but not "
            "sufficient - a system can be infrastructure-green while "
            "business-level requests are actually failing.\n\n"
            "Strong answers: name every hop in the request path explicitly "
            "(not just 'it goes to Kubernetes'), distinguish the "
            "Kubernetes-side config from the cloud-side resources it "
            "provisions, and explain troubleshooting as checking both "
            "sides rather than assuming the problem is in one place.\n\n"
            "Weak answers / red flags: 'LoadBalancer distributes traffic to "
            "pods' with no further detail, an inability to explain what's "
            "actually created on the cloud side, or claiming that green "
            "infrastructure metrics prove the application is working "
            "correctly."
        ),
        "automation": (
            "Core mechanics: Production-grade container hardening includes "
            "multi-stage builds (heavy build tools stay in a discarded "
            "builder stage), pinning the base image by exact SHA256 digest "
            "rather than a mutable tag (a tag can point to different "
            "content over time; a digest identifies exact image content, "
            "which matters for reproducibility and supply-chain security), "
            "running as a dedicated non-root UID/GID, and copying only "
            "built artifacts into a minimal runtime base. For "
            "infrastructure-as-code: Terraform should use remote state "
            "with locking so two concurrent `apply` runs can't corrupt "
            "shared state or create conflicting changes; if `apply` fails "
            "halfway through, the right move is to inspect what was "
            "actually created (state reflects partial success) and re-plan "
            "after fixing the underlying issue, not to blindly destroy and "
            "restart. A real CI/CD pipeline has quality gates that "
            "shouldn't be skipped under deadline pressure - typically "
            "build, automated tests, security/image scanning, and a "
            "deploy step with smoke tests or automated rollback on "
            "failure. Secrets belong in a secret manager (Vault, cloud "
            "KMS) or are retrieved via short-lived workload identity "
            "(OIDC) - never committed to Git or passed as long-lived "
            "static credentials.\n\n"
            "Strong answers: explain WHY each hardening step matters (not "
            "just naming it), understand Terraform state as the source of "
            "truth for reconciliation rather than something to nuke and "
            "retry, and describe secrets as retrieved via identity/"
            "authentication rather than stored as plain values.\n\n"
            "Weak answers / red flags: treating multi-stage builds or "
            "digest pinning as boxes to check rather than explaining the "
            "actual risk each addresses, suggesting `terraform destroy` as "
            "a first response to a failed apply, or describing secrets "
            "management as 'we put it in an environment variable.'"
        ),
        "technical_aptitude": (
            "Core mechanics: Pods hang in Terminating mainly due to (1) a "
            "storage unmount failure - an open file handle/lock on a "
            "PersistentVolume blocks the pvc-protection finalizer - or (2) "
            "an orphaned custom finalizer left by a crashed/removed "
            "operator. Never force-delete (`--grace-period=0`) a stateful "
            "workload without verifying the process is actually dead on "
            "the node, since it may still be running and cause "
            "dual-primary data corruption. When only a subset of requests "
            "or users are failing (not a total outage), the right "
            "instinct is to compare successful vs failed requests by "
            "backend/pod/node/AZ rather than assuming the whole "
            "application is broken - sticky sessions, a single bad pod, "
            "or a specific request pattern are common causes. TLS can "
            "terminate at the cloud load balancer, a shared reverse proxy, "
            "or the ingress (with or without re-encryption to the "
            "backend) - certificate rotation should provision and "
            "validate the new cert before removing the old one, never "
            "delete-then-replace. A container working locally but failing "
            "in production is almost always an environment difference: "
            "missing env vars/config, a CPU architecture mismatch, a "
            "root-vs-non-root permission difference, or different "
            "network/DNS rules - not usually 'the container is broken.' A "
            "pod reported Running and Ready by Kubernetes does not "
            "guarantee the application is correct - Kubernetes health "
            "checks may not exercise the actual failing code path.\n\n"
            "Strong answers: distinguish partial failure from total "
            "outage before forming a hypothesis, describe an actual "
            "investigation sequence (not just a list of things to check), "
            "explicitly reject unsafe shortcuts (force-delete, restart "
            "everything) with a reason, and - when asked about a real "
            "incident - can walk through what they initially thought, "
            "what evidence proved that wrong, and what was actually "
            "happening.\n\n"
            "Weak answers / red flags: jumping straight to 'restart the "
            "pods' or 'check the logs' with no diagnostic sequence, "
            "claiming Kubernetes-reported health guarantees application "
            "correctness, an inability to explain what evidence would "
            "distinguish a partial failure from a total one, or an "
            "incident story that stays at 'we found the bug and fixed it' "
            "with no wrong-turn or investigation detail."
        ),
        "continuous_delivery": (
            "Core mechanics: Policy-as-code admission control (e.g. "
            "Kyverno, OPA/Gatekeeper) enforces guardrails at the cluster "
            "level so bad configs are rejected before they run, not caught "
            "after the fact in code review - this matters because code "
            "review alone doesn't stop a misconfigured pipeline or a "
            "manual `kubectl apply`. A deployment being reported "
            "successful only means the deployment controller accepted the "
            "manifests; it does not mean the application works, so "
            "validation after deploy (readiness checks, smoke tests, "
            "canary traffic + error-rate monitoring) is a separate, "
            "necessary step. Rolling updates, blue-green, and canary are "
            "different risk/rollback trade-offs: rolling reuses the same "
            "environment with gradual replacement, blue-green runs both "
            "versions and switches traffic (fast rollback), canary sends "
            "a small percentage of traffic first to limit blast radius "
            "before expanding. Knowing a fix 'worked' means validating "
            "the original failure condition is actually resolved (the "
            "specific error rate, latency, or symptom), not just "
            "confirming the deploy succeeded.\n\n"
            "Strong answers: describe post-deploy validation as a "
            "required step, not an afterthought; correctly reason about "
            "which deployment strategy fits a given risk level and why; "
            "and describe validating a fix against the original symptom, "
            "not against the deploy status.\n\n"
            "Weak answers / red flags: treating 'the deployment succeeded' "
            "as proof the change worked, being unable to explain the "
            "actual difference between rolling/blue-green/canary beyond "
            "naming them, or describing policy enforcement as something "
            "code review already handles."
        ),
        "communication": (
            "Core mechanics: Translating a technical incident for a "
            "non-technical audience means describing business impact and "
            "what was done, not implementation detail - e.g. 'a subset of "
            "application instances stopped processing requests correctly; "
            "we redirected traffic away from them and restored service; "
            "we're now fixing why our health checks didn't catch it "
            "sooner' rather than explaining pod internals. When asked "
            "about something genuinely unfamiliar, an honest answer "
            "relates it to something the candidate has actually used and "
            "explains what they'd verify, rather than fabricating "
            "hands-on expertise. A root cause analysis should distinguish "
            "the immediate technical symptom (e.g. 'the pod returned "
            "500') from the actual root cause (e.g. 'validation was "
            "missing so a bad config reached production'), and end with a "
            "corrective action that's an engineering control, not just "
            "updated documentation. Communicating during an active outage "
            "follows roughly: mitigate/restore service first, stabilize, "
            "then investigate root cause, then correct and prevent - not "
            "attempting a full RCA while customers are still down.\n\n"
            "Strong answers: translate technical detail into business "
            "impact and next steps without jargon, are honest about the "
            "limits of their direct experience rather than inventing it, "
            "and can clearly separate 'what broke' from 'why it broke' "
            "from 'what we did about it.'\n\n"
            "Weak answers / red flags: an explanation so technical a "
            "non-engineer couldn't follow it, fabricated confidence about "
            "tools/platforms they haven't actually used, or an incident "
            "explanation that never gets past the symptom to an actual "
            "root cause."
        ),
    },
}


def get_question_for_role_competency(
    role: str, competency_key: str, label: str, candidate_id: str = ""
) -> str:
    """Picks a variant deterministically based on the candidate's own
    ID, not a shared counter. This means:
    - Different candidates land on different variants (no coordination
      needed between requests)
    - The same candidate always sees the same question if they reload
    - Completely immune to server restarts, since nothing depends on
      in-memory state that can be wiped (a real problem with the old
      rotating-counter approach, which reset to the same first variant
      every time the dev server restarted - which happens often)."""
    role_bank = QUESTION_BANK.get(role)
    if not role_bank:
        from app.roles import DEFAULT_ROLE
        role_bank = QUESTION_BANK.get(DEFAULT_ROLE, {})

    variants = role_bank.get(competency_key)
    if not variants:
        return f"Describe your experience related to {label} and give a concrete, real-world example."

    if not candidate_id:
        return variants[0]

    digest = hashlib.md5(f"{candidate_id}:{role}:{competency_key}".encode()).hexdigest()
    idx = int(digest, 16) % len(variants)

    return variants[idx]


# Per-question reference answers, index-aligned with QUESTION_BANK - each
# entry here corresponds to the QUESTION_BANK entry at the same index for
# that role+competency. This enables get_reference_for_specific_question()
# below to fetch the EXACT reference material for the specific question a
# candidate was actually asked, instead of a generic blob covering every
# variant. Only populated for roles/competencies where this exists (right
# now: backend-engineer, sourced from Backend_Developer_AI_Question_Bank.xlsx
# plus 15 hand-written entries matching the same style for the 3 original
# questions per competency that predate that spreadsheet).
QUESTION_REFERENCE_ANSWERS: Dict[str, Dict[str, List[Dict[str, str]]]] = {
    "backend-engineer": {
        "breadth_of_knowledge": [
            {"strong": "I'd start by checking the database's own lock/wait diagnostics (e.g. pg_stat_activity or a slow query log) to see if the query is actually blocked waiting on another transaction, versus just slow to execute. If it's not lock contention, I'd check the query plan for a missing or unused index - the same query can behave very differently once data volume crosses a threshold. If the plan looks fine, I'd check connection pool metrics (active vs max connections, wait time to acquire a connection) since exhaustion looks identical to 'slow query' from the caller's side but has a completely different fix.", "weak": "I'd probably just restart the service or increase the timeout value, since I haven't had to dig into locking or connection pool internals directly before."},
            {"strong": "First I'd check whether it's actually the service or a downstream dependency - database connection pool exhaustion, a slow external call, or CPU/memory saturation on the instance itself. Second, I'd check whether requests are being queued or rejected at a load balancer or ingress layer before even reaching the service. Third, I'd check for a resource limit that only bites at higher concurrency, like a thread pool size or a database connection pool sized for 100 rps, not 500.", "weak": "I'd check the logs and probably just scale up the number of instances, without a clear plan for confirming that's actually the bottleneck first."},
            {"strong": "I'd explain that 'always correct instantly, everywhere' has a real cost - either in latency (waiting for every replica to agree) or availability (rejecting requests during a partition). I'd translate it to their world: for a bank balance, we probably want strong consistency because being wrong is unacceptable; for a 'like count' or a search index, eventual consistency is fine because a few seconds of staleness costs nothing and buys us speed and resilience. I'd ask which specific behavior they're actually worried about instead of promising 'always correct' as a blanket property.", "weak": "I'd just say we'll add more caching and syncing to make sure everything is always accurate, without really addressing the underlying trade-off."},
            {"strong": "Immutability guarantees an object is always in a valid state once created, eliminating a whole category of bugs from unexpected mutation elsewhere in the codebase, and makes reasoning about concurrent or shared code much simpler. Putting validation in the constructor means an invalid object can never exist in the first place, rather than being created invalid and caught later.", "weak": "I initially put validation logic in the constructor but, when asked why, wasn't able to explain why that's preferable to validating elsewhere or not at all."},
            {"strong": "I'd return an unmodifiable/defensive copy or view of the collection rather than the live internal reference, so callers can read it but any attempt to mutate it either fails fast or has no effect on the object's real internal state - this protects encapsulation, which is the whole point of keeping the field private in the first place.", "weak": "I don't see why this matters - if the field is private, I'd assume it's already protected regardless of what a getter returns."},
            {"strong": "As soon as a concept has more than two meaningfully distinct states, or the transitions between states carry rules (e.g. some transitions are invalid), I model it explicitly - a dedicated type makes illegal states unrepresentable, is far easier to assert against in tests, and documents the domain concept instead of leaving it implicit in a combination of flags scattered around the code.", "weak": "I didn't create a dedicated model for status in my own solution, which made it hard for me to assert on certain scenarios during testing, and I wasn't able to clearly explain an alternative when asked."},
            {"strong": "I look at who truly owns the invariant: if the value only makes sense in the context of a single item and needs its own validation rules (e.g. quantity can't go negative for that item), it belongs on the item itself, with the item exposing behaviour to change it safely. The parent aggregate should then coordinate across items rather than reaching in and mutating their internals directly, which keeps each object responsible for protecting its own state.", "weak": "In a prior implementation I updated a value like quantity directly from the parent/collection level, even though it was really a property of the item itself, and wasn't able to justify a different placement when it was raised with me."},
            {"strong": "I avoid 'primitive obsession' - a raw map or a loose collection of primitives has no way to enforce its own invariants and pushes validation logic out to every place that uses it. A dedicated class gives the concept a name, a single place to validate and evolve it, and makes the code self-documenting; I'd reach for a class or record as soon as a group of related values starts being passed around together.", "weak": "In a past implementation I kept most of the logic operating on raw dictionaries with no separation between items and pricing, and even with hints during review I didn't arrive at a dedicated-model design."},
            {"strong": "double and float use binary floating-point representation, which cannot exactly represent many decimal fractions (like 0.1), so repeated arithmetic accumulates small rounding errors that are unacceptable for money. BigDecimal represents decimal numbers exactly and lets you control scale and rounding mode explicitly, which is essential when totals need to be precise to the cent and auditable.", "weak": "I used a double variable to represent price in a prior implementation and, when asked, wasn't able to explain why BigDecimal would have been a better choice."},
            {"strong": "I'd centralise rounding in one place - e.g. a single utility or a dedicated method on the money/price type - always specifying an explicit scale and rounding mode such as HALF_UP, rather than letting each call site round independently with potentially different modes. This avoids subtle discrepancies where two paths compute the 'same' total slightly differently.", "weak": "I haven't given specific thought to rounding mode consistency; I generally just call whatever rounding function is convenient at each call site."},
            {"strong": "I'd validate as close to the point of entry as possible - ideally in the constructor or a factory method of the domain object itself - so an invalid quantity can never exist as a valid instance, throwing a clear, specific exception rather than silently clamping or ignoring it. I'd also cover this with an explicit test for the boundary and invalid cases.", "weak": "In a previous implementation there was no validation on the quantity field, and I hadn't identified this as a gap until it was raised with me."},
            {"strong": "I'd use a map-based merge keyed by a unique identifier for the item, using the collection's built-in merge/compute operation to add the new quantity to any existing entry in a single, expressive line, rather than manually looping through a list, checking for an existing match, and branching on whether it was found.", "weak": "I hadn't thought about merging duplicate entries specifically and would likely just keep appending new entries even when the same item is added more than once."},
            {"strong": "BigDecimal's equals() considers both value and scale, so 2.0 and 2.00 are NOT equal under equals() even though they represent the same number - I'd use compareTo() == 0 (or setScale to a common scale first) when I only care about numeric value, and reserve equals() for cases where I genuinely want scale to matter too, such as exact representation checks.", "weak": "I'm not aware of any difference between equals() and compareTo() for BigDecimal and would treat them as interchangeable."},
        ],
        "automation": [
            {"strong": "The manual process required someone to run a script by hand against production with a checklist, which meant a real risk of running steps out of order, skipping a step under time pressure, or running it against the wrong environment entirely. I automated it into a pipeline stage that requires the same reviewed script every time, runs in a fixed order, and can't be run against production without the same approvals as any other deploy - removing the human-memory dependency was the actual risk reduction, not just saving time.", "weak": "I've mostly followed existing automated migration processes rather than converting a manual one myself, so I don't have a concrete example of what specifically improved."},
            {"strong": "I'd design the migration to be idempotent and broken into small reversible steps, each with a corresponding down-migration, so a partial failure can be rolled back step by step rather than needing a single all-or-nothing undo. I'd also have the pipeline capture exactly which step it reached before failing, so the rollback tooling knows precisely how far to unwind rather than guessing.", "weak": "I'd probably just restore from a backup if something went wrong, without an automated rollback path specific to the migration itself."},
            {"strong": "I'd push back specifically on the word 'quick' - a small change to a shared API is exactly the kind of thing that causes an incident precisely because it looked low-risk. I'd offer to help write a fast, focused test rather than a full suite, so it doesn't meaningfully slow them down, and explain that the test is protecting whoever touches this code next, not just validating today's change.", "weak": "I'd probably let it go if we were under deadline pressure, since enforcing testing standards isn't something I'd push hard on in the moment."},
            {"strong": "I write one small failing test that describes the next bit of behaviour I want (red), write the simplest possible code to make just that test pass without worrying about elegance (green), then refactor the implementation and/or the test for clarity while keeping all tests passing - and repeat, one small increment at a time, letting the design emerge rather than pre-planning the whole class up front.", "weak": "I said I was familiar with TDD, but when asked to apply it I ended up writing the implementation logic directly inside the test method rather than separating test and production code."},
            {"strong": "Unit tests should exercise a single class's logic in isolation with all external dependencies mocked or faked, so they're fast, deterministic, and don't depend on network availability. Integration tests are kept separate and deliberately smaller in number, covering just the handful of scenarios that verify the real wiring, without duplicating every unit-test scenario against the live dependency.", "weak": "I couldn't clearly justify why some of my tests used mocks, some used a real client, and some were integration-style - the reasoning behind the split wasn't something I could explain when asked."},
            {"strong": "A mock is a pre-programmed test double where you set expectations on calls and typically verify interactions happened as expected, often used to fully replace a dependency and assert on how it was used. A spy wraps a real object and records calls made to it while still optionally delegating to the real implementation, useful when you want real behaviour for most of the object but need to verify or override specific interactions.", "weak": "I could differentiate mock and spy at a theoretical level when asked, but hadn't actually applied a spy, or an equivalent to mocking an external dependency, in an integration test where it would have been the more appropriate choice."},
            {"strong": "I write a failing test that expresses the new rule first, run it to confirm it fails for the right reason, then write the minimal implementation to make it pass. This keeps the test honest and forces me to think about the rule's edge cases before I get absorbed in implementation details.", "weak": "I add the logic directly and only add a test if asked to, or if I need to prove a bug fix; test-first isn't part of how I currently work."},
            {"strong": "I'd override equals()/hashCode() on the object to define what business equality means, and then assert directly using that. If I needed to compare using an ordering method like compareTo, I'd only do so because equals() genuinely can't express the comparison, and I'd be able to explain exactly why compareTo()==0 was the right check rather than equals().", "weak": "I used an assertion comparing objects via compareTo in a test but wasn't able to explain why that approach was necessary or what problem it was solving when asked."},
            {"strong": "Typically: commit triggers a build and static analysis/lint; then automated unit tests, then broader integration/contract tests; a code coverage and quality gate check; a security/dependency vulnerability scan; artifact packaging; deployment to a staging or pre-prod environment often with automated smoke/E2E tests; and finally a controlled production deployment with automated rollback if health checks fail post-deploy.", "weak": "My experience with CI/CD pipelines is limited, and I wasn't able to describe test distribution or pipeline stages with much confidence when asked."},
            {"strong": "Anything repeatable, objective, and fast enough to run on every change - unit/integration tests, linting, security/dependency scans, code coverage thresholds - should be automated, since manual repetition of these is slow, inconsistent, and doesn't scale. Manual checks are reserved for things requiring human judgement that's hard to codify.", "weak": "My experience with the automated-vs-manual balance in a pipeline is limited; I don't have strong hands-on exposure to configuring these checks myself."},
            {"strong": "Feature flags decouple deployment from release, letting you ship code to production dark, then enable it gradually and roll it back instantly by flipping the flag rather than redeploying if something goes wrong. Before relying on one, I'd think about flag lifecycle, how flag state is tested in combination, and monitoring to know when it's safe to fully enable.", "weak": "I'm not familiar with feature flags/toggles or their purpose in production deployments."},
            {"strong": "I'd favour trunk-based development with small, frequent merges to main gated by CI, combined with feature flags for anything not ready to be user-facing - this keeps main continuously releasable and avoids long-lived branches that accumulate painful merge conflicts.", "weak": "I don't have much hands-on experience reasoning about branching strategy in relation to deployability specifically."},
            {"strong": "At minimum: all automated tests passing, a code review approval from at least one other engineer, a passing security/dependency vulnerability scan, code coverage not regressing below an agreed threshold, and a deliberate go/no-go check informed by monitoring/alerting readiness for higher-risk changes.", "weak": "I don't have significant hands-on experience with formal quality gates as part of a release process."},
        ],
        "technical_aptitude": [
            {"strong": "I'd use a tiered approach - a generous per-API-key limit for legitimate customers using a token bucket or sliding window algorithm, plus a stricter, IP-based or anomaly-based limit layered on top to catch abusive traffic that isn't tied to a known key. The trade-off is complexity versus fairness: a single flat limit is simple but either throttles good customers or lets abuse through.", "weak": "I'd just set one global rate limit for everyone and adjust the number if customers complain, without differentiating abusive from legitimate traffic."},
            {"strong": "I wouldn't actually make it required at the API level right away - I'd add it as optional with a sensible default, update all clients to start sending it, monitor adoption, and only enforce it as truly required once I've confirmed every client has migrated. Calling it 'required' before every consumer can supply it is what breaks existing clients.", "weak": "I'd add the field as required and let the clients that break come back with error reports, then fix it reactively."},
            {"strong": "I'd reach for a message queue when the caller doesn't need an immediate response, when the receiving service might be temporarily unavailable and shouldn't block the caller, or when I want to decouple the two services' deploy/scaling lifecycles. I'd use a direct synchronous call when the caller genuinely needs the result to proceed and a slight coupling in availability is an acceptable trade-off for simplicity.", "weak": "I'd default to whichever one is already used elsewhere in the codebase, without a specific reason tied to this particular case."},
            {"strong": "I look at whether the class has more than one reason to change - for example, if it both fetches external data and performs business calculations, a change to either concern forces me to touch the same file. I'd extract each concern into its own class with a single, clearly named responsibility.", "weak": "I don't tend to actively split classes based on responsibility; if it compiles and passes tests I generally leave the structure as it is unless there's a specific bug forcing a change."},
            {"strong": "It lets the consuming code depend on an abstraction rather than an implementation, so I can substitute a fake or mock in unit tests without any network calls, and swap the real implementation later without touching the calling code - this follows the Dependency Inversion Principle.", "weak": "I don't see a strong need for an interface if there's only one implementation; I'd just call the concrete class directly and mock at the HTTP layer if tests need it."},
            {"strong": "I favour composition whenever the relationship is 'has-a' rather than a true 'is-a', or when I expect behaviour to vary independently at runtime - composition avoids fragile base-class problems and keeps classes focused.", "weak": "I haven't thought much about the trade-off - I pick whichever is quicker to write for the immediate case."},
            {"strong": "I'd look at extending behaviour rather than modifying the existing code path directly - for example adding a new method or a small strategy/policy object the existing flow can plug into. I'd write a failing test for the new rule first, confirm the existing suite still passes, then implement.", "weak": "I'd implement the requirement in the way that's fastest to get working, and only think about existing tests if they start failing."},
            {"strong": "Tight coupling means a class knows too much about another's internals, so a change in one forces a change in the other; loose coupling means classes interact through narrow, stable abstractions. I'd pull the calculation logic out into its own class, have the original class depend on an interface for the external call, and inject that dependency.", "weak": "I'm not confident distinguishing tight and loose coupling in concrete code, and would likely leave both responsibilities in the same class."},
            {"strong": "I'd look at where the system actually hurts in practice - recurring incidents, slow deploys, hard-to-test areas - and prioritise based on impact and frequency rather than personal preference, connecting the technical decision back to a business or reliability outcome.", "weak": "I walked through the components of my project only at a very high level and wasn't able to go deeper into technical details or pain points even with additional prompting."},
            {"strong": "I'd weigh factors like fit for the problem, team familiarity, community support and long-term maintenance risk, performance under expected load, and integration with the existing stack - and I can walk through a real decision including an alternative that was seriously considered and why it lost out.", "weak": "I wasn't able to speak in much depth about why particular frameworks or technologies were used on my project when asked, even with some nudging."},
            {"strong": "I'd consider how credentials/secrets are stored and rotated, whether the connection is encrypted in transit, input validation on data coming back from the external service, rate limiting and abuse protection, least-privilege scoping of API keys, and what happens if the third party is compromised or returns malicious data.", "weak": "I don't have much hands-on experience specifically evaluating security concerns for third-party integrations."},
            {"strong": "I'd first want to know where the actual bottleneck is via profiling/metrics rather than guessing - CPU-bound, I/O-bound, or memory-related. From there I'd consider caching, horizontal scaling, asynchronous processing, or backpressure - always tying the technique back to the actual bottleneck and discussing real trade-offs like cache invalidation complexity.", "weak": "I don't have hands-on experience reasoning through a real performance or scaling incident."},
            {"strong": "Failures become partial and asynchronous by default, so I design for idempotency, think explicitly about eventual consistency instead of assuming immediate consistency, and use contract testing between services rather than relying purely on slow, brittle end-to-end tests. I'd also expect dead-letter queues, retry/backoff policies, and distributed tracing across service boundaries.", "weak": "I don't have meaningful exposure to microservices or event-driven systems to answer this from experience."},
        ],
        "continuous_delivery": [
            {"strong": "I'd do this as an expand-and-contract migration: first add the new structure alongside the old one and have writes populate both, then backfill historical data, then migrate readers over one at a time with the ability to roll back, and only remove the old structure once every dependent service has fully switched over and been verified.", "weak": "I'd schedule a maintenance window and migrate everything at once, coordinating with other teams to all deploy together."},
            {"strong": "I'd wrap the risky code path behind a flag that can be toggled per percentage of traffic, deploy the change fully dark, then enable it for a small canary cohort first while watching error rates and latency, only ramping up as confidence builds - keeping the old path reachable via the same flag for instant rollback without a redeploy.", "weak": "I'd deploy the change to everyone at once and watch the dashboards closely, planning to roll back the whole deploy if something breaks."},
            {"strong": "I'd make sure the migration is backward-compatible with the currently-running application version at every intermediate step - for example adding a new nullable column rather than renaming one in place - so old code keeps working while the migration runs. I'd also run it in small batches rather than one long-locking transaction.", "weak": "I'd run the migration during off-peak hours and hope the lock duration is short enough not to cause a noticeable issue."},
            {"strong": "I'd extract a dedicated client class solely responsible for making the external call, parsing the response, and translating errors into meaningful exceptions, and have the orchestrating service depend on that client through an interface. A change to the API's shape then only touches the client, not the business rules.", "weak": "I couldn't clearly justify why calling an external API directly from business/domain logic is a code smell when asked, and my implementation kept them tightly coupled."},
            {"strong": "I look for a service accumulating unrelated responsibilities over time, often revealed by the class needing to know about multiple unrelated concerns to make a single decision. I'd split it by extracting each cohesive responsibility into its own class and have the original become a thin coordinator.", "weak": "I designed a service to hold a reference and also be responsible for calculations and rounding, and while I could explain my reasoning when asked, I hadn't proactively identified that as a separate concern worth splitting out."},
            {"strong": "If the calculation is a core, stable part of what the domain concept 'is', I'd put it on the domain model so the model can't be used incorrectly. If it depends on external, changeable policy like region-based rates, I'd extract it into a separate policy/service so changing the rule doesn't require touching the core domain object.", "weak": "In a past implementation, I created a separate service purely to hold a calculation that could have simply lived on the model itself, and wasn't able to give a clear reason for the extra abstraction when it was questioned."},
            {"strong": "If the abstraction is just a thin pass-through with no added logic, validation, or alternative implementation ever expected, it's likely trivial. I'd check whether removing it and inlining its one caller changes the design meaningfully; if not, I'd fold it back in.", "weak": "I created an abstraction for a calculation that added no real value beyond what the calling class could have done itself, and wasn't able to justify the extra layer when it was raised with me."},
            {"strong": "I'd design the component to depend on an interface for the external interaction rather than a concrete client, injected via the constructor, so tests can supply a fake implementation that returns controlled responses instantly and deterministically, covering both success and failure paths.", "weak": "I hadn't specifically designed for isolated testability here and my tests for this kind of logic tended to depend on the real external service being available."},
            {"strong": "Metrics for aggregate health and trends that power dashboards and alerting; structured logs with correlation IDs to investigate a specific failure after the fact; and distributed traces to follow a single request across service boundaries and pinpoint where time is spent - each answers a different question, and I'd set alerting thresholds that map to real user impact.", "weak": "I have limited experience with observability tooling in production systems."},
            {"strong": "I'd have automated dependency and container scanning run on every build, fail the build on critical severity findings that have a fix available, and track lower-severity findings with a clear owner rather than ignoring them. When a scan flags something, I'd assess actual exploitability in context before deciding whether it blocks a release.", "weak": "I don't have meaningful hands-on experience with vulnerability scanning as part of a delivery pipeline."},
            {"strong": "Authentication answers 'who are you', while authorization answers 'what are you allowed to do' - conflating the two is a common source of security bugs. I'd rely on established standards like OAuth2/OIDC rather than rolling my own, and apply authorization checks as close as possible to the resource being protected.", "weak": "I'm not confident distinguishing authentication from authorization or describing how I'd implement either."},
            {"strong": "Detection would come from alerting tied to meaningful thresholds rather than someone noticing manually. On alert, I'd triage using dashboards/traces to narrow down what changed recently, mitigate first if possible before fully root-causing, communicate status to stakeholders, and run a blameless post-incident review afterward.", "weak": "I don't have meaningful hands-on experience with production incident response."},
            {"strong": "I'd look for signals beyond 'it works': product/usage metrics showing the feature is actually used as intended, direct user feedback, and support/ticket trends after release. I try to stay close to why a feature is being built so I can flag early if it doesn't seem likely to achieve that outcome.", "weak": "I haven't given much thought to feedback loops beyond confirming the code passes tests and meets the stated requirement."},
        ],
        "communication": [
            {"strong": "I'd give them concrete specifics well ahead of time - exactly what's changing, a realistic migration deadline, and ideally a period where both old and new behavior work side by side so their migration isn't a hard cutover on my timeline. I'd frame it in terms of what breaks for them specifically, not just describe the change from my side.", "weak": "I'd send an email announcing the change and expect teams to read the changelog and adjust on their own."},
            {"strong": "I'd tell them as soon as I had real evidence the estimate was wrong, not close to the original deadline, and explain specifically what changed rather than a vague 'it's taking longer.' I'd come with options - reduced scope on the original date, or full scope on a new date - so they have a real decision to make.", "weak": "I mentioned it was going to be late once I was already past the deadline, without much detail on why or what the new plan was."},
            {"strong": "I'd describe the actual user-facing impact in plain terms, give a realistic sense of what's being done right now and when they can expect an update, and be honest if I don't yet know the ETA rather than guessing to sound reassuring. I'd keep updates coming at a predictable interval even if there's no new information.", "weak": "I'd give a technical explanation of what's happening internally and let them ask follow-up questions if they're confused."},
            {"strong": "I'd create a small hierarchy or set of distinct, specific exception types for each meaningful failure mode - e.g. a 'resource not found' exception separate from a generic 'service unavailable' exception - so calling code can catch and react to each case appropriately instead of doing string-matching scattered through business logic.", "weak": "I hadn't thought about differentiating failure types for an external call and would likely catch everything with one broad catch block."},
            {"strong": "I'd wrap it when the lower-level exception exposes implementation details the caller shouldn't need to know about, preserving the original as the 'cause' so the stack trace is never lost, while giving callers a stable exception type to catch against. I'd let it propagate unwrapped only when the caller genuinely needs the low-level detail.", "weak": "I've caught and effectively swallowed exceptions before, like an empty catch block or just logging, rather than wrapping and rethrowing them, without a strong reason for doing so."},
            {"strong": "I use checked exceptions for failure cases the caller can reasonably be expected to recover from and where I want the compiler to force explicit handling, and unchecked exceptions for programming errors or unrecoverable conditions where forcing every caller to catch them would just add boilerplate.", "weak": "I'm not clear on the practical difference between checked and unchecked exceptions beyond that one requires a try/catch or throws declaration."},
            {"strong": "I'd treat 'not found' as an explicit, distinct outcome rather than an unexpected error - either a specific typed exception or a result type that forces the calling code to handle the absence case deliberately - and make sure this scenario has its own test so the system's behaviour is well-defined, not left inconsistent.", "weak": "In a previous implementation, a not-found scenario left the containing object in an inconsistent state, and I was only able to identify the issue after it was pointed out."},
            {"strong": "A library/client should surface specific, well-documented exception types without making assumptions about how the caller wants to react - logging, retrying, or failing fast is a decision for the application, which catches those types and translates them into context-appropriate behaviour.", "weak": "I haven't specifically considered this distinction and would likely just add a try/catch wherever an error currently surfaces."},
            {"strong": "I use AI tools for acceleration - scaffolding boilerplate, exploring an approach quickly - but I still review every suggestion critically, run and read the tests myself, and make sure I fully understand and can explain any code before it's merged, since I'm ultimately accountable for it.", "weak": "I haven't given much thought to how AI tool usage should be balanced against maintaining engineering quality."},
            {"strong": "Risks include subtly incorrect logic that looks plausible, security vulnerabilities baked into suggested code, and the developer's own understanding atrophying if they stop engaging critically. I'd mitigate this with tests that actually verify behaviour, human code review, and explaining the code back in my own words before merging.", "weak": "I haven't considered risks of over-reliance on AI tools in development."},
            {"strong": "Switching isn't as simple as swapping an API endpoint - different models differ in how they were trained and tuned and their behaviour on edge cases, so prompts and evaluation results tuned for one model may not transfer cleanly. I'd want a proper evaluation suite and re-testing pass before treating a model switch as low-risk.", "weak": "I don't have enough familiarity with how different AI models/providers differ to comment on the risks of switching between them."},
            {"strong": "I narrate my thinking as I go rather than going quiet while typing - flagging when I'm choosing between two viable approaches and why, and explicitly inviting my partner's input at natural decision points rather than presenting a finished decision.", "weak": "In a pairing exercise, I was told I engaged well in communication but didn't explain what I was doing during the coding itself."},
            {"strong": "I engage with the suggestion genuinely rather than defending my original approach by default - I'll quickly weigh whether it's actually better, and if it is, refactor promptly rather than finishing my original path first out of momentum or attachment.", "weak": "When my approach was questioned, I remained firm that the existing design was appropriate rather than genuinely engaging with whether a different approach might be better."},
        ],
    },
}


def get_reference_for_specific_question(role: str, competency_key: str, candidate_id: str) -> str:
    """Replays the exact same deterministic hash used by
    get_question_for_role_competency() to pick the candidate's
    question variant, so scoring can use that SPECIFIC question's
    reference answers instead of a generic per-competency blob covering
    every variant. This is both more accurate (only the actually-asked
    question's material, not a diluted mix) and smaller per prompt
    (one question's reference, not ten) than the older approach.

    Falls back to the generic per-competency reference for any
    role/competency that doesn't have per-question data yet (e.g.
    DevOps, or any role added later without this level of detail)."""
    variants = QUESTION_BANK.get(role, {}).get(competency_key)
    per_question = QUESTION_REFERENCE_ANSWERS.get(role, {}).get(competency_key)

    if not variants or not per_question or len(per_question) != len(variants):
        return get_reference_for_role_competency(role, competency_key)

    digest = hashlib.md5(f"{candidate_id}:{role}:{competency_key}".encode()).hexdigest()
    idx = int(digest, 16) % len(variants)

    question_text = variants[idx]
    ref = per_question[idx]

    return (
        f'The candidate was specifically asked: "{question_text}"\n\n'
        f"A strong (score 5) answer looks like: {ref['strong']}\n\n"
        f"A weak (score 1) answer looks like: {ref['weak']}"
    )


def get_reference_for_role_competency(role: str, competency_key: str) -> str:
    return REFERENCE_KNOWLEDGE.get(role, {}).get(competency_key, "")


# --- Backwards-compatible wrappers (old call signature, DevOps only) ---
def get_question_for_competency(competency_key: str, label: str, candidate_id: str = "") -> str:
    return get_question_for_role_competency("operability-engineer", competency_key, label, candidate_id)


def get_reference_for_competency(competency_key: str) -> str:
    return get_reference_for_role_competency("operability-engineer", competency_key)