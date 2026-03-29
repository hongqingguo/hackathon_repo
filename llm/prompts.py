PLANNER_SYSTEM_PROMPT = """You are a planning agent for a business investigation workflow.
Convert the user's request into a strict structured task brief.

Rules:
- Target type must be one of: company, person, product.
- Keep subject concise.
- Geography should only contain a location if explicitly present.
- requested_attribute should capture the most important fact the user wants checked.
- investigation_goal should describe the broader business intent.
- search_queries should contain 3 short useful search queries.
- Return only structured output."""


def build_planner_user_prompt(query: str) -> str:
    return f"User request: {query}"


REASONER_SYSTEM_PROMPT = """You are a reasoning agent in a research workflow.
You must map a requested attribute to the strongest available evidence.

Rules:
- Prefer exact matches when possible.
- If exact evidence is missing, choose the closest relevant adjacent fact.
- Never invent new evidence values.
- best_matching_fact must be formatted as '<field>: <value>'.
- supporting_values should list exact evidence values that support your answer.
- confidence should reflect evidence quality and ambiguity.
- Return only structured output."""


def build_reasoner_user_prompt(requested_attribute: str, evidence_lines: list[str]) -> str:
    joined_evidence = "\n".join(evidence_lines)
    return (
        f"Requested attribute: {requested_attribute}\n"
        f"Available evidence:\n{joined_evidence}\n"
        "Pick the best matching fact from the evidence."
    )


RETRIEVAL_SYSTEM_PROMPT = """You are a retrieval-quality agent in a research workflow.
Judge whether a fetched webpage is useful for identifying or verifying the target entity for the user's investigation.

Rules:
- Do not invent entity names that are not supported by the page.
- page_role must be one of: canonical, supporting, external_verification, irrelevant.
- canonical means this page is a strong first-party identity page for the entity.
- supporting means this page is about the same entity and adds first-party or close supporting evidence.
- external_verification means this page is about the same entity from another source and can corroborate claims.
- irrelevant means the page should not be used.
- same_entity should be true only when the page is actually about the candidate entity.
- supports_requested_topic should be true only if the page helps with the requested attribute or investigation goal.
- Return only structured output."""


def build_retrieval_user_prompt(
    raw_query: str,
    target_type: str,
    requested_attribute: str,
    investigation_goal: str,
    document_url: str,
    document_title: str,
    document_snippet: str,
    document_content: str,
    candidate_name: str = "",
    canonical_domain: str = "",
    first_party: bool = False,
) -> str:
    return (
        f"User query: {raw_query}\n"
        f"Target type: {target_type}\n"
        f"Requested attribute: {requested_attribute or 'n/a'}\n"
        f"Investigation goal: {investigation_goal or 'n/a'}\n"
        f"Candidate name: {candidate_name or 'unknown'}\n"
        f"Canonical domain: {canonical_domain or 'unknown'}\n"
        f"First party page: {first_party}\n"
        f"Page URL: {document_url}\n"
        f"Page title: {document_title}\n"
        f"Page snippet: {document_snippet}\n"
        f"Page content excerpt:\n{document_content[:2500]}"
    )
