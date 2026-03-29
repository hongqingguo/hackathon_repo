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
