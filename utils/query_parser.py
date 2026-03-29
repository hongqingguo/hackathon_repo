import re

from utils.schemas import SearchBrief


KNOWN_ENTITY_TYPES = {
    "company": ["company", "companies", "startup", "startups", "vendor", "vendors"],
    "person": ["person", "people", "founder", "founders", "executive", "executives"],
    "product": ["product", "products", "tool", "tools", "platform", "platforms"],
}

KNOWN_GEOGRAPHIES = [
    "new york",
    "nyc",
    "san francisco",
    "boston",
    "chicago",
]

KNOWN_ATTRIBUTES = [
    "cto",
    "vp engineering",
    "head of ai",
    "coo",
    "founder",
    "pricing",
    "security",
    "integrations",
    "compliance",
]


def parse_query(query: str) -> SearchBrief:
    normalized_query = " ".join(query.split())
    lower_query = normalized_query.lower()
    target_type = _infer_target_type(lower_query)
    geography = _first_match(lower_query, KNOWN_GEOGRAPHIES)
    requested_attribute = _first_match(lower_query, KNOWN_ATTRIBUTES)
    subject, investigation_goal = _extract_subject_and_goal(
        normalized_query,
        target_type,
        geography,
        requested_attribute,
    )

    search_queries = [
        normalized_query,
        f"{subject} {requested_attribute}".strip(),
        f"{target_type} {subject} {investigation_goal}".strip(),
    ]

    return SearchBrief(
        raw_query=normalized_query,
        target_type=target_type,
        subject=subject,
        geography=geography or "",
        requested_attribute=requested_attribute or "",
        investigation_goal=investigation_goal,
        search_queries=search_queries,
    )


def _infer_target_type(query: str) -> str:
    for target_type, keywords in KNOWN_ENTITY_TYPES.items():
        if any(keyword in query for keyword in keywords):
            return target_type
    return "company"


def _first_match(query: str, options: list[str]) -> str:
    for option in options:
        if option in query:
            return option
    return ""


def _extract_goal(query: str) -> str:
    lower_query = query.lower()
    triggers = ["with", "about", "for", "that", "regarding"]
    positions = [lower_query.find(f" {trigger} ") for trigger in triggers if lower_query.find(f" {trigger} ") != -1]
    if positions:
        start = min(positions)
        trigger = lower_query[start:].split(" ", 2)[1]
        remainder = query[start + len(trigger) + 2 :].strip(" .")
        if remainder:
            return remainder
    return "relevant facts"


def _extract_subject_and_goal(
    query: str, target_type: str, geography: str, requested_attribute: str
) -> tuple[str, str]:
    working = query.strip()
    working = re.sub(r"^(find|check|compare|validate|verify)\s+", "", working, flags=re.IGNORECASE)

    goal = _extract_goal(working)
    lower_working = working.lower()
    for trigger in [" with ", " about ", " for ", " that ", " regarding "]:
        index = lower_working.find(trigger)
        if index != -1:
            working = working[:index].strip()
            break

    if geography:
        geo_pattern = re.compile(rf"\bin\s+{re.escape(geography)}\b", re.IGNORECASE)
        working = geo_pattern.sub("", working)

    cleanup_terms = [geography, requested_attribute]
    cleanup_terms.extend(KNOWN_ENTITY_TYPES.get(target_type, []))
    for term in cleanup_terms:
        if term:
            working = re.sub(rf"\b{re.escape(term)}\b", "", working, flags=re.IGNORECASE)

    subject = " ".join(working.split()).strip(" ,.")
    return subject or target_type, goal
