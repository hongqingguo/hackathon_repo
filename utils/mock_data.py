from utils.schemas import CandidateEntity


MOCK_ENTITIES = [
    CandidateEntity(
        name="FlowStack",
        entity_type="company",
        canonical_url="https://flowstack.example.com",
        location="New York, NY",
        summary="A growing SaaS platform modernizing internal approvals and operations for distributed teams.",
        tags=["saas", "automation", "operations"],
        facts=[
            {
                "field": "leadership_role",
                "value": "VP Engineering",
                "source_url": "https://flowstack.example.com/team",
                "snippet": "Meet Dana Kim, VP Engineering, leading platform reliability and developer productivity.",
            },
            {
                "field": "leadership_role",
                "value": "Head of Operations",
                "source_url": "https://flowstack.example.com/about",
                "snippet": "Operations leadership is focused on scaling service delivery with lean internal tooling.",
            },
            {
                "field": "category",
                "value": "SaaS workflow automation",
                "source_url": "https://flowstack.example.com",
                "snippet": "FlowStack is a SaaS workflow automation platform for distributed teams.",
            },
        ],
        signals=[
            {
                "label": "manual approval bottlenecks",
                "source_url": "https://flowstack.example.com/careers",
                "snippet": "We are investing in systems to reduce manual approval bottlenecks across teams.",
            },
            {
                "label": "manual approval bottlenecks",
                "source_url": "https://flowstack.example.com/blog/ops-at-scale",
                "snippet": "Our operations team is focused on removing manual approval bottlenecks as we scale.",
            },
            {
                "label": "workflow automation",
                "source_url": "https://flowstack.example.com/blog/platform-scale",
                "snippet": "Our next phase depends on better workflow automation for cross-functional processes.",
            },
        ],
    ),
    CandidateEntity(
        name="LedgerLeap",
        entity_type="company",
        canonical_url="https://ledgerleap.example.com",
        location="New York, NY",
        summary="A fintech startup building embedded finance tools for modern vertical software platforms.",
        tags=["fintech", "infrastructure", "api"],
        facts=[
            {
                "field": "leadership_role",
                "value": "CTO",
                "source_url": "https://ledgerleap.example.com/team",
                "snippet": "The founding CTO leads product architecture, compliance engineering, and platform growth.",
            },
            {
                "field": "leadership_role",
                "value": "Director of Operations",
                "source_url": "https://ledgerleap.example.com/company",
                "snippet": "Operations leadership supports onboarding, compliance workflows, and partner delivery.",
            },
            {
                "field": "category",
                "value": "Fintech infrastructure",
                "source_url": "https://ledgerleap.example.com",
                "snippet": "LedgerLeap provides fintech infrastructure for embedded finance workflows.",
            },
        ],
        signals=[
            {
                "label": "compliance workflow complexity",
                "source_url": "https://ledgerleap.example.com/blog/scaling-compliance",
                "snippet": "Scaling compliance workflows is becoming one of our biggest operational challenges.",
            },
            {
                "label": "compliance workflow complexity",
                "source_url": "https://ledgerleap.example.com/careers",
                "snippet": "We are hiring operators who can reduce compliance workflow complexity across onboarding.",
            }
        ],
    ),
    CandidateEntity(
        name="Northstar Health",
        entity_type="company",
        canonical_url="https://northstarhealth.example.com",
        location="Boston, MA",
        summary="A healthtech analytics company helping care networks unify fragmented operational data.",
        tags=["healthtech", "analytics", "data"],
        facts=[
            {
                "field": "leadership_role",
                "value": "Head of Data",
                "source_url": "https://northstarhealth.example.com/team",
                "snippet": "The Head of Data owns clinical analytics infrastructure and internal data systems.",
            },
            {
                "field": "leadership_role",
                "value": "COO",
                "source_url": "https://northstarhealth.example.com/about",
                "snippet": "The COO oversees scaling operations across provider partnerships.",
            },
            {
                "field": "category",
                "value": "Healthtech analytics",
                "source_url": "https://northstarhealth.example.com",
                "snippet": "Northstar Health delivers healthtech analytics for provider networks.",
            },
        ],
        signals=[
            {
                "label": "data integration friction",
                "source_url": "https://northstarhealth.example.com/resources/interoperability",
                "snippet": "Healthcare partners still face major data integration friction.",
            }
        ],
    ),
    CandidateEntity(
        name="Dana Kim",
        entity_type="person",
        canonical_url="https://flowstack.example.com/team/dana-kim",
        location="New York, NY",
        summary="An engineering executive focused on platform reliability and developer productivity.",
        tags=["executive", "engineering", "platform"],
        facts=[
            {
                "field": "current_role",
                "value": "VP Engineering",
                "source_url": "https://flowstack.example.com/team",
                "snippet": "Dana Kim serves as VP Engineering at FlowStack.",
            },
            {
                "field": "expertise",
                "value": "platform reliability",
                "source_url": "https://flowstack.example.com/team/dana-kim",
                "snippet": "Dana specializes in platform reliability and engineering execution.",
            },
            {
                "field": "expertise",
                "value": "developer productivity",
                "source_url": "https://speakerhub.example.com/dana-kim",
                "snippet": "Dana Kim often speaks about developer productivity and internal tooling.",
            },
        ],
        signals=[
            {
                "label": "technical budget influence",
                "source_url": "https://flowstack.example.com/team",
                "snippet": "Dana leads platform investment priorities across engineering.",
            }
        ],
    ),
    CandidateEntity(
        name="OpsPilot AI",
        entity_type="product",
        canonical_url="https://opspilot.example.com",
        location="San Francisco, CA",
        summary="An AI operations product focused on approvals, task routing, and internal workflow automation.",
        tags=["product", "ai", "operations", "workflow"],
        facts=[
            {
                "field": "pricing_model",
                "value": "contact sales",
                "source_url": "https://opspilot.example.com/pricing",
                "snippet": "Pricing is available through a contact-sales plan for enterprise teams.",
            },
            {
                "field": "integrations",
                "value": "Slack, Jira, Salesforce",
                "source_url": "https://opspilot.example.com/integrations",
                "snippet": "OpsPilot AI integrates with Slack, Jira, and Salesforce.",
            },
            {
                "field": "category",
                "value": "AI workflow automation",
                "source_url": "https://opspilot.example.com",
                "snippet": "OpsPilot AI is an AI workflow automation product for operations teams.",
            },
        ],
        signals=[
            {
                "label": "enterprise workflow automation",
                "source_url": "https://opspilot.example.com/customers",
                "snippet": "Customers use OpsPilot AI to automate enterprise workflow approvals.",
            }
        ],
    ),
]
