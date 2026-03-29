import os
import re
from typing import List, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests import Response

from llm.config import get_llm_provider, has_openai_config
from llm.retrieval_service import RetrievalLLM
from utils.mock_data import MOCK_ENTITIES
from utils.schemas import CandidateEntity, SearchBrief, SourceDocument


_RETRIEVAL_STATS = {
    "provider": "",
    "llm_successes": 0,
    "fallbacks": 0,
    "last_error": "",
}


def search_entities(brief: SearchBrief) -> List[CandidateEntity]:
    backend = (brief.search_backend or os.getenv("SEARCH_BACKEND", "mock")).strip().lower()
    if backend == "mock":
        return _search_mock_entities(brief)
    if backend in {"live", "tavily"}:
        return _search_live_entities(brief, backend)
    raise ValueError(f"Unsupported SEARCH_BACKEND: {backend}")


def reset_retrieval_stats() -> None:
    _RETRIEVAL_STATS["provider"] = get_llm_provider()
    _RETRIEVAL_STATS["llm_successes"] = 0
    _RETRIEVAL_STATS["fallbacks"] = 0
    _RETRIEVAL_STATS["last_error"] = ""


def get_retrieval_stats() -> dict:
    return dict(_RETRIEVAL_STATS)


def discover_search_urls(brief: SearchBrief) -> List[str]:
    backend = (brief.search_backend or os.getenv("SEARCH_BACKEND", "mock")).strip().lower()
    return _discover_urls(brief, backend)


def fetch_source_document(url: str) -> Optional[SourceDocument]:
    return _fetch_document(url)


def fetch_root_document(document: SourceDocument) -> Optional[SourceDocument]:
    return _fetch_root_document(document)


def expand_first_party_documents(
    brief: SearchBrief,
    primary_document: SourceDocument,
    root_document: Optional[SourceDocument],
) -> List[SourceDocument]:
    return _expand_domain_documents(brief, primary_document, root_document)


def select_canonical_document(brief: SearchBrief, documents: List[SourceDocument]) -> Optional[SourceDocument]:
    return _select_canonical_document(brief, documents)


def infer_candidate_name(brief: SearchBrief, canonical_document: SourceDocument) -> str:
    return _infer_candidate_name(brief, canonical_document)


def add_cross_domain_documents(
    brief: SearchBrief,
    candidate_name: str,
    canonical_document: SourceDocument,
    source_documents: List[SourceDocument],
) -> List[SourceDocument]:
    backend = (brief.search_backend or os.getenv("SEARCH_BACKEND", "mock")).strip().lower()
    return _add_cross_domain_documents(brief, backend, candidate_name, canonical_document, source_documents)


def build_candidate_entity(
    brief: SearchBrief,
    candidate_name: str,
    canonical_document: SourceDocument,
    primary_document: SourceDocument,
    source_documents: List[SourceDocument],
) -> CandidateEntity:
    return _candidate_from_documents(brief, candidate_name, canonical_document, primary_document, source_documents)


def _search_mock_entities(brief: SearchBrief) -> List[CandidateEntity]:
    scored_candidates = []
    for entity in MOCK_ENTITIES:
        score = 0
        haystack = " ".join(
            [
                entity.name,
                entity.entity_type,
                entity.location,
                entity.summary,
                " ".join(entity.tags),
                " ".join(fact["value"] for fact in entity.facts),
                " ".join(signal["label"] for signal in entity.signals),
            ]
        ).lower()

        if entity.entity_type == brief.target_type:
            score += 3
        if brief.subject and brief.subject.lower() in haystack:
            score += 3
        if brief.geography and brief.geography.lower() in entity.location.lower():
            score += 2
        if brief.requested_attribute:
            requested_terms = [term for term in brief.requested_attribute.lower().split() if len(term) > 2]
            score += sum(1 for term in requested_terms if term in haystack)
        if brief.investigation_goal:
            goal_terms = [term for term in brief.investigation_goal.lower().split() if len(term) > 3]
            score += sum(1 for term in goal_terms if term in haystack)

        if score > 0:
            scored_candidates.append((score, entity))

    scored_candidates.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored_candidates[:10]]


def _search_live_entities(brief: SearchBrief, backend: str) -> List[CandidateEntity]:
    urls = _discover_urls(brief, backend)
    candidates: List[CandidateEntity] = []
    seen_domains: set[str] = set()
    for url in urls[:12]:
        primary_document = _fetch_document(url)
        if not primary_document or primary_document.domain in seen_domains:
            continue

        root_document = _fetch_root_document(primary_document)
        first_party_documents = _expand_domain_documents(brief, primary_document, root_document)
        canonical_document = _select_canonical_document(brief, first_party_documents)
        if not canonical_document:
            continue

        candidate_name = _infer_candidate_name(brief, canonical_document)
        source_documents = _add_cross_domain_documents(
            brief=brief,
            backend=backend,
            candidate_name=candidate_name,
            canonical_document=canonical_document,
            source_documents=first_party_documents,
        )
        candidates.append(
            _candidate_from_documents(
                brief=brief,
                candidate_name=candidate_name,
                canonical_document=canonical_document,
                primary_document=primary_document,
                source_documents=source_documents,
            )
        )
        seen_domains.add(canonical_document.domain)
    return candidates


def _discover_urls(brief: SearchBrief, backend: str) -> List[str]:
    queries = brief.search_queries or [brief.raw_query]
    if backend == "tavily":
        discovered = _discover_urls_via_tavily(queries)
        if discovered:
            return discovered
    return _discover_urls_via_duckduckgo(queries)


def _discover_urls_via_duckduckgo(search_queries: List[str]) -> List[str]:
    discovered: List[str] = []
    seen: set[str] = set()
    for query in search_queries[:4]:
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            response = _http_get(search_url)
            response.raise_for_status()
        except Exception:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.select("a.result__a"):
            href = _normalize_result_url(anchor.get("href", "").strip())
            if href and href not in seen:
                seen.add(href)
                discovered.append(href)
            if len(discovered) >= 20:
                return discovered
    return discovered


def _discover_urls_via_tavily(search_queries: List[str]) -> List[str]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    discovered: List[str] = []
    seen: set[str] = set()
    for query in search_queries[:4]:
        try:
            response = _http_post_json(
                "https://api.tavily.com/search",
                {
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": 6,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            continue

        for item in payload.get("results", []):
            url = str(item.get("url", "")).strip()
            if url and url not in seen:
                seen.add(url)
                discovered.append(url)
            if len(discovered) >= 20:
                return discovered
    return discovered


def _fetch_document(url: str) -> Optional[SourceDocument]:
    try:
        response = _http_get(url)
        response.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    snippet = meta.get("content", "").strip() if meta else ""
    content = " ".join(text.strip() for text in soup.stripped_strings)[:5000]
    return SourceDocument(
        url=url,
        domain=_normalize_domain(url),
        title=title,
        snippet=snippet[:500],
        content=content,
    )


def _fetch_root_document(document: SourceDocument) -> Optional[SourceDocument]:
    parsed = urlparse(document.url)
    root_url = f"{parsed.scheme}://{parsed.netloc}/"
    if root_url == document.url:
        return document
    return _fetch_document(root_url)


def _expand_domain_documents(
    brief: SearchBrief,
    primary_document: SourceDocument,
    root_document: Optional[SourceDocument],
) -> List[SourceDocument]:
    seed_documents = _combine_documents(primary_document, root_document)
    scored_links: dict[str, int] = {}
    for document in seed_documents:
        for url, score in _discover_relevant_links(brief, document).items():
            scored_links[url] = max(scored_links.get(url, 0), score)

    documents = list(seed_documents)
    seen_urls = {document.url for document in documents}
    for url, _score in sorted(scored_links.items(), key=lambda item: item[1], reverse=True):
        if len(documents) >= 5:
            break
        if url in seen_urls:
            continue
        fetched = _fetch_document(url)
        if not fetched:
            continue
        documents.append(fetched)
        seen_urls.add(url)
    unique: dict[str, SourceDocument] = {document.url: document for document in documents}
    return list(unique.values())


def _discover_relevant_links(brief: SearchBrief, document: SourceDocument) -> dict[str, int]:
    try:
        response = _http_get(document.url)
        response.raise_for_status()
    except Exception:
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    base_domain = _normalize_domain(document.url)
    keywords = _candidate_keywords(brief)
    scored_links: dict[str, int] = {}
    for anchor in soup.select("a[href]"):
        resolved = _normalize_candidate_link(document.url, anchor.get("href", "").strip())
        if not resolved or _normalize_domain(resolved) != base_domain:
            continue
        anchor_text = " ".join(anchor.stripped_strings).lower()
        haystack = f"{resolved.lower()} {anchor_text}"
        score = _keyword_overlap_score(keywords, haystack)
        if urlparse(resolved).path.count("/") <= 2:
            score += 1
        if score > 0:
            scored_links[resolved] = max(scored_links.get(resolved, 0), score)
    return scored_links


def _select_canonical_document(brief: SearchBrief, documents: List[SourceDocument]) -> Optional[SourceDocument]:
    scored: List[tuple[float, SourceDocument]] = []
    for document in documents:
        assessment = _assess_document(
            brief=brief,
            document=document,
            candidate_name="",
            canonical_domain=document.domain,
            first_party=True,
        )
        if not assessment["same_entity"]:
            continue
        if assessment["page_role"] == "irrelevant":
            continue
        score = float(assessment["relevance_score"])
        if assessment["page_role"] == "canonical":
            score += 0.2
        scored.append((score, document))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def _infer_candidate_name(brief: SearchBrief, canonical_document: SourceDocument) -> str:
    assessment = _assess_document(
        brief=brief,
        document=canonical_document,
        candidate_name="",
        canonical_domain=canonical_document.domain,
        first_party=True,
    )
    if assessment["entity_name"]:
        return assessment["entity_name"]
    return _infer_name_from_document(canonical_document)


def _add_cross_domain_documents(
    brief: SearchBrief,
    backend: str,
    candidate_name: str,
    canonical_document: SourceDocument,
    source_documents: List[SourceDocument],
) -> List[SourceDocument]:
    queries = _build_corroboration_queries(brief, candidate_name)
    urls = _discover_urls_via_tavily(queries) if backend == "tavily" else _discover_urls_via_duckduckgo(queries)
    combined = list(source_documents)
    seen_urls = {document.url for document in combined}
    seen_domains = {document.domain for document in combined}
    for url in urls:
        if len(combined) >= 7:
            break
        document = _fetch_document(url)
        if not document or document.url in seen_urls or document.domain == canonical_document.domain:
            continue
        if document.domain in seen_domains:
            continue
        assessment = _assess_document(
            brief=brief,
            document=document,
            candidate_name=candidate_name,
            canonical_domain=canonical_document.domain,
            first_party=False,
        )
        if not assessment["same_entity"]:
            continue
        if not assessment["supports_requested_topic"]:
            continue
        combined.append(document)
        seen_urls.add(document.url)
        seen_domains.add(document.domain)
    return combined


def _build_corroboration_queries(brief: SearchBrief, candidate_name: str) -> List[str]:
    return [
        f"\"{candidate_name}\" {brief.requested_attribute} {brief.investigation_goal}".strip(),
        f"\"{candidate_name}\" {brief.subject} {brief.requested_attribute}".strip(),
        f"\"{candidate_name}\" {brief.target_type} {brief.investigation_goal}".strip(),
    ]


def _candidate_from_documents(
    brief: SearchBrief,
    candidate_name: str,
    canonical_document: SourceDocument,
    primary_document: SourceDocument,
    source_documents: List[SourceDocument],
) -> CandidateEntity:
    summary = canonical_document.snippet or canonical_document.content[:240]
    signals = []
    for document in source_documents:
        signals.extend(_infer_signals(brief, document))

    facts = _build_facts(brief, candidate_name, canonical_document, primary_document, source_documents)
    return CandidateEntity(
        name=candidate_name,
        entity_type=brief.target_type,
        canonical_url=canonical_document.url,
        location=_infer_location(brief, canonical_document),
        summary=summary,
        tags=_infer_tags(brief, canonical_document),
        facts=facts,
        signals=_dedupe_signal_dicts(signals),
        source_documents=source_documents,
    )


def _build_facts(
    brief: SearchBrief,
    candidate_name: str,
    canonical_document: SourceDocument,
    primary_document: SourceDocument,
    source_documents: List[SourceDocument],
) -> List[dict]:
    facts = [
        {
            "field": "canonical_title",
            "value": canonical_document.title or candidate_name,
            "source_url": canonical_document.url,
            "snippet": canonical_document.snippet or canonical_document.content[:180],
        }
    ]
    if primary_document.url != canonical_document.url:
        facts.append(
            {
                "field": "discovery_page_title",
                "value": primary_document.title or primary_document.domain,
                "source_url": primary_document.url,
                "snippet": primary_document.snippet or primary_document.content[:180],
            }
        )

    seen = {(item["field"], item["source_url"]) for item in facts}
    for document in source_documents:
        field = _document_fact_field(document, canonical_document.domain)
        if (field, document.url) in seen:
            continue
        facts.append(
            {
                "field": field,
                "value": document.title or _infer_name_from_document(document),
                "source_url": document.url,
                "snippet": document.snippet or document.content[:180],
            }
        )
        seen.add((field, document.url))
    if brief.subject:
        facts.append(
            {
                "field": "query_subject",
                "value": brief.subject,
                "source_url": canonical_document.url,
                "snippet": canonical_document.snippet or canonical_document.content[:180],
            }
        )
    return facts


def _document_fact_field(document: SourceDocument, canonical_domain: str) -> str:
    path = urlparse(document.url).path.lower()
    if document.domain != canonical_domain:
        return "external_reference_title"
    if any(term in path for term in ["pricing", "plan", "plans", "cost"]):
        return "pricing_page_title"
    if any(term in path for term in ["integration", "connector", "api"]):
        return "integration_page_title"
    if any(term in path for term in ["feature", "product", "platform", "solution"]):
        return "product_page_title"
    if any(term in path for term in ["about", "team", "leadership", "company", "profile"]):
        return "company_profile_page_title"
    return "page_title"


def _infer_name_from_document(document: SourceDocument) -> str:
    title = _clean_title(document.title)
    if title:
        return title
    return _domain_to_name(document.domain)


def _clean_title(title: str) -> str:
    if not title:
        return ""
    candidate = title.split("|")[0].strip()
    parts = [part.strip() for part in re.split(r"\s[-:]\s", candidate) if part.strip()]
    if parts:
        candidate = max(parts, key=len)
    return candidate.strip()


def _infer_location(brief: SearchBrief, document: SourceDocument) -> str:
    content_lower = document.content.lower()
    for location in ["new york", "nyc", "san francisco", "boston", "chicago"]:
        if location in content_lower:
            return location.title()
    return brief.geography.title() if brief.geography else ""


def _infer_tags(brief: SearchBrief, document: SourceDocument) -> List[str]:
    tags = [brief.target_type]
    for term in (brief.subject or "").split():
        if len(term) > 3:
            tags.append(term.lower())
    tags.append(document.domain.split(".")[0].lower())
    return sorted(set(tags))


def _infer_signals(brief: SearchBrief, document: SourceDocument) -> List[dict]:
    signals = []
    content_lower = document.content.lower()
    terms = [brief.requested_attribute, brief.investigation_goal, brief.subject]
    for term in terms:
        if not term:
            continue
        normalized = term.strip().lower()
        if len(normalized) < 4:
            continue
        if normalized in content_lower:
            signals.append(
                {
                    "label": normalized,
                    "source_url": document.url,
                    "snippet": document.snippet or document.content[:180],
                }
            )
    return signals


def _assess_document(
    brief: SearchBrief,
    document: SourceDocument,
    candidate_name: str,
    canonical_domain: str,
    first_party: bool,
) -> dict:
    if has_openai_config():
        try:
            result = RetrievalLLM().invoke(
                raw_query=brief.raw_query,
                target_type=brief.target_type,
                requested_attribute=brief.requested_attribute,
                investigation_goal=brief.investigation_goal,
                document_url=document.url,
                document_title=document.title,
                document_snippet=document.snippet,
                document_content=document.content,
                candidate_name=candidate_name,
                canonical_domain=canonical_domain,
                first_party=first_party,
            ).model_dump()
            _RETRIEVAL_STATS["provider"] = get_llm_provider()
            _RETRIEVAL_STATS["llm_successes"] += 1
            return result
        except Exception as exc:
            _RETRIEVAL_STATS["provider"] = get_llm_provider()
            _RETRIEVAL_STATS["fallbacks"] += 1
            _RETRIEVAL_STATS["last_error"] = f"{type(exc).__name__}: {exc}"
    return _fallback_assessment(brief, document, candidate_name, first_party)


def _fallback_assessment(
    brief: SearchBrief,
    document: SourceDocument,
    candidate_name: str,
    first_party: bool,
) -> dict:
    text = f"{document.title} {document.snippet} {document.content[:2000]}".lower()
    score = min(1.0, 0.2 + 0.08 * sum(1 for keyword in _candidate_keywords(brief) if keyword in text))
    same_entity = True
    if candidate_name:
        tokens = [token for token in re.split(r"[^a-z0-9]+", candidate_name.lower()) if len(token) > 2]
        same_entity = any(token in text for token in tokens) if tokens else True
    supports_requested_topic = any(
        term and term.lower() in text for term in [brief.requested_attribute, brief.investigation_goal, brief.subject]
    )
    page_role = "supporting"
    if first_party and urlparse(document.url).path in {"", "/"}:
        page_role = "canonical"
    elif not first_party and same_entity and supports_requested_topic:
        page_role = "external_verification"
    elif not supports_requested_topic and not first_party:
        page_role = "irrelevant"
    return {
        "entity_name": candidate_name or _infer_name_from_document(document),
        "page_role": page_role,
        "same_entity": same_entity,
        "supports_requested_topic": supports_requested_topic,
        "relevance_score": round(score, 2),
        "reasoning_note": "fallback_assessment",
    }


def _candidate_keywords(brief: SearchBrief) -> List[str]:
    keywords = [brief.target_type, brief.subject, brief.requested_attribute, brief.investigation_goal]
    normalized = []
    for keyword in keywords:
        if not keyword:
            continue
        normalized.extend(part.strip().lower() for part in keyword.split() if len(part.strip()) > 2)
    return sorted(set(normalized))


def _keyword_overlap_score(keywords: List[str], haystack: str) -> int:
    return sum(2 for keyword in keywords if keyword and keyword in haystack)


def _normalize_candidate_link(base_url: str, href: str) -> str:
    if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
        return ""
    resolved = _normalize_result_url(urljoin(base_url, href))
    parsed = urlparse(resolved)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return resolved


def _normalize_result_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        query = parse_qs(parsed.query)
        target = query.get("uddg", [""])[0]
        if target:
            return unquote(target)
    return url


def _normalize_domain(url: str) -> str:
    hostname = urlparse(url).netloc.lower().strip()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def _combine_documents(primary_document: SourceDocument, root_document: Optional[SourceDocument]) -> List[SourceDocument]:
    documents = [primary_document]
    if root_document and root_document.url != primary_document.url:
        documents.append(root_document)
    unique: dict[str, SourceDocument] = {}
    for document in documents:
        unique[document.url] = document
    return list(unique.values())


def _dedupe_signal_dicts(signals: List[dict]) -> List[dict]:
    unique: dict[tuple[str, str], dict] = {}
    for signal in signals:
        unique[(signal["label"], signal["source_url"])] = signal
    return list(unique.values())


def _domain_to_name(domain: str) -> str:
    root = domain.split(".")[0].replace("-", " ").strip()
    return " ".join(part.capitalize() for part in root.split())


def _http_get(url: str) -> Response:
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}
    try:
        return requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.ProxyError:
        session = requests.Session()
        session.trust_env = False
        return session.get(url, headers=headers, timeout=10)


def _http_post_json(url: str, payload: dict) -> Response:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    try:
        return requests.post(url, headers=headers, json=payload, timeout=15)
    except requests.exceptions.ProxyError:
        session = requests.Session()
        session.trust_env = False
        return session.post(url, headers=headers, json=payload, timeout=15)
