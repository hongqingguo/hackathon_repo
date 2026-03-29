import os
from typing import List, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests import Response

from utils.mock_data import MOCK_ENTITIES
from utils.schemas import CandidateEntity, SearchBrief, SourceDocument


EDITORIAL_DOMAINS = {
    "medium.com",
    "substack.com",
    "techcrunch.com",
    "forbes.com",
}

TARGET_PATH_HINTS = {
    "product": ["pricing", "integrations", "features", "product", "platform", "customers"],
    "company": ["about", "team", "leadership", "customers", "solutions", "careers"],
    "person": ["about", "team", "bio", "leadership", "speaker", "profile"],
}


def search_entities(brief: SearchBrief) -> List[CandidateEntity]:
    backend = (brief.search_backend or os.getenv("SEARCH_BACKEND", "mock")).strip().lower()
    if backend == "mock":
        return _search_mock_entities(brief)
    if backend in {"live", "tavily"}:
        return _search_live_entities(brief, backend)
    raise ValueError(f"Unsupported SEARCH_BACKEND: {backend}")


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
        if not primary_document:
            continue
        domain = primary_document.domain
        if domain in seen_domains:
            continue

        root_document = _fetch_root_document(primary_document)
        source_documents = _expand_domain_documents(brief, primary_document, root_document)
        canonical_document = _select_canonical_document(brief, primary_document, root_document, source_documents)
        if _should_skip_document(brief, canonical_document, source_documents):
            continue

        candidate = _candidate_from_documents(brief, canonical_document, primary_document, source_documents)
        candidates.append(candidate)
        seen_domains.add(domain)
    return candidates


def _discover_urls(brief: SearchBrief, backend: str) -> List[str]:
    if backend == "tavily":
        discovered = _discover_urls_via_tavily(brief.search_queries or [brief.raw_query])
        if discovered:
            return discovered
    return _discover_urls_via_duckduckgo(brief.search_queries or [brief.raw_query])


def _discover_urls_via_duckduckgo(search_queries: List[str]) -> List[str]:
    discovered: List[str] = []
    seen: set[str] = set()
    for query in search_queries[:3]:
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            response = _http_get(search_url)
            response.raise_for_status()
        except Exception:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.select("a.result__a"):
            href = anchor.get("href", "").strip()
            href = _normalize_result_url(href)
            if href and href not in seen:
                seen.add(href)
                discovered.append(href)
            if len(discovered) >= 15:
                return discovered
    return discovered


def _discover_urls_via_tavily(search_queries: List[str]) -> List[str]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    discovered: List[str] = []
    seen: set[str] = set()
    for query in search_queries[:3]:
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
            if len(discovered) >= 15:
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
    content = " ".join(text.strip() for text in soup.stripped_strings)
    content = content[:4000]
    domain = _normalize_domain(url)
    return SourceDocument(
        url=url,
        domain=domain,
        title=title,
        snippet=snippet[:500],
        content=content,
    )


def _candidate_from_documents(
    brief: SearchBrief,
    canonical_document: SourceDocument,
    primary_document: SourceDocument,
    source_documents: List[SourceDocument],
) -> CandidateEntity:
    name = _infer_name_from_document(canonical_document)
    summary = canonical_document.snippet or canonical_document.content[:240]
    signals = []
    for document in source_documents:
        signals.extend(_infer_signals(brief, document))

    facts = _build_facts(brief, canonical_document, primary_document, source_documents, name)
    if primary_document.url != canonical_document.url:
        facts.append(
            {
                "field": "discovery_page_title",
                "value": primary_document.title or primary_document.domain,
                "source_url": primary_document.url,
                "snippet": primary_document.snippet or primary_document.content[:180],
            }
        )
    if brief.subject:
        facts.append(
            {
                "field": "query_subject",
                "value": brief.subject,
                "source_url": canonical_document.url,
                "snippet": canonical_document.snippet or canonical_document.content[:180],
            }
        )

    return CandidateEntity(
        name=name,
        entity_type=brief.target_type,
        canonical_url=canonical_document.url,
        location=_infer_location(brief, canonical_document),
        summary=summary,
        tags=_infer_tags(brief, canonical_document),
        facts=facts,
        signals=_dedupe_signal_dicts(signals),
        source_documents=source_documents,
    )


def _infer_name_from_document(document: SourceDocument) -> str:
    if document.title:
        return document.title.split("|")[0].split("-")[0].strip() or document.domain
    return _domain_to_name(document.domain)


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
    domain = document.domain.split(".")[0]
    tags.append(domain.lower())
    return sorted(set(tags))


def _infer_signals(brief: SearchBrief, document: SourceDocument) -> List[dict]:
    signals = []
    content_lower = document.content.lower()
    interesting_terms = [
        brief.requested_attribute,
        brief.investigation_goal,
        "pricing",
        "integration",
        "security",
        "compliance",
        "automation",
        "workflow",
        "founder",
    ]
    for term in interesting_terms:
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


def _build_facts(
    brief: SearchBrief,
    canonical_document: SourceDocument,
    primary_document: SourceDocument,
    source_documents: List[SourceDocument],
    name: str,
) -> List[dict]:
    facts = [
        {
            "field": "canonical_title",
            "value": canonical_document.title or name,
            "source_url": canonical_document.url,
            "snippet": canonical_document.snippet or canonical_document.content[:180],
        }
    ]
    if brief.subject:
        facts.append(
            {
                "field": "query_subject",
                "value": brief.subject,
                "source_url": canonical_document.url,
                "snippet": canonical_document.snippet or canonical_document.content[:180],
            }
        )

    seen_fact_keys = {(item["field"], item["source_url"]) for item in facts}
    for document in source_documents:
        field = _document_fact_field(document)
        if (field, document.url) in seen_fact_keys:
            continue
        facts.append(
            {
                "field": field,
                "value": document.title or _infer_name_from_document(document),
                "source_url": document.url,
                "snippet": document.snippet or document.content[:180],
            }
        )
        seen_fact_keys.add((field, document.url))
    return facts


def _document_fact_field(document: SourceDocument) -> str:
    path = urlparse(document.url).path.lower()
    if "pricing" in path:
        return "pricing_page_title"
    if "integration" in path or "connector" in path or "api" in path:
        return "integration_page_title"
    if "feature" in path or "product" in path or "platform" in path:
        return "product_page_title"
    if "about" in path or "team" in path or "leadership" in path:
        return "company_profile_page_title"
    return "page_title"


def _normalize_domain(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.netloc.lower().strip()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


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
            current_score = scored_links.get(url, 0)
            if score > current_score:
                scored_links[url] = score

    expanded_documents = list(seed_documents)
    fetched_urls = {document.url for document in expanded_documents}
    ranked_urls = sorted(scored_links.items(), key=lambda item: item[1], reverse=True)
    for url, _score in ranked_urls:
        if len(expanded_documents) >= 5:
            break
        if url in fetched_urls:
            continue
        document = _fetch_document(url)
        if not document:
            continue
        expanded_documents.append(document)
        fetched_urls.add(url)

    unique: dict[str, SourceDocument] = {}
    for document in expanded_documents:
        unique[document.url] = document
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
        href = anchor.get("href", "").strip()
        resolved = _normalize_candidate_link(document.url, href)
        if not resolved:
            continue
        if _normalize_domain(resolved) != base_domain:
            continue

        anchor_text = " ".join(anchor.stripped_strings).lower()
        haystack = f"{resolved.lower()} {anchor_text}"
        score = 0
        for keyword in keywords:
            if keyword and keyword in haystack:
                score += 2
        for hint in TARGET_PATH_HINTS.get(brief.target_type, []):
            if hint in haystack:
                score += 3
        if score > 0:
            scored_links[resolved] = max(scored_links.get(resolved, 0), score)
    return scored_links


def _candidate_keywords(brief: SearchBrief) -> List[str]:
    keywords = [brief.requested_attribute, brief.subject, brief.investigation_goal]
    keywords.extend(TARGET_PATH_HINTS.get(brief.target_type, []))
    keywords.extend(["pricing", "integration", "security", "api", "demo", "product"])
    normalized = []
    for keyword in keywords:
        if not keyword:
            continue
        normalized.extend(part.strip().lower() for part in keyword.split() if len(part.strip()) > 2)
    return sorted(set(normalized))


def _normalize_candidate_link(base_url: str, href: str) -> str:
    if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
        return ""
    resolved = _normalize_result_url(urljoin(base_url, href))
    parsed = urlparse(resolved)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return resolved


def _select_canonical_document(
    brief: SearchBrief,
    primary_document: SourceDocument,
    root_document: Optional[SourceDocument],
    source_documents: List[SourceDocument],
) -> SourceDocument:
    candidates = [doc for doc in source_documents if not _looks_editorial(doc)]
    if root_document and not _looks_editorial(root_document):
        candidates.insert(0, root_document)
    if not candidates:
        return root_document or primary_document

    ranked = sorted(candidates, key=lambda doc: _document_quality_score(brief, doc), reverse=True)
    return ranked[0]


def _document_quality_score(brief: SearchBrief, document: SourceDocument) -> int:
    score = 0
    text = f"{document.title} {document.snippet} {document.content[:1200]}".lower()
    if _looks_vendor_like(document):
        score += 6
    if not _looks_editorial(document):
        score += 3
    for hint in TARGET_PATH_HINTS.get(brief.target_type, []):
        if hint in text or hint in document.url.lower():
            score += 2
    if brief.requested_attribute and brief.requested_attribute.lower() in text:
        score += 3
    if brief.subject:
        for part in brief.subject.lower().split():
            if len(part) > 3 and part in text:
                score += 1
    parsed = urlparse(document.url)
    if parsed.path in {"", "/"}:
        score += 1
    return score


def _should_skip_document(brief: SearchBrief, canonical_document: SourceDocument, source_documents: List[SourceDocument]) -> bool:
    if canonical_document.domain in EDITORIAL_DOMAINS:
        return True
    if brief.target_type != "product":
        return False

    vendor_like_count = sum(1 for doc in source_documents if _looks_vendor_like(doc))
    editorial_count = sum(1 for doc in source_documents if _looks_editorial(doc))
    return vendor_like_count == 0 or (editorial_count >= len(source_documents) and not _looks_vendor_like(canonical_document))


def _looks_editorial(document: SourceDocument) -> bool:
    url_path = urlparse(document.url).path.lower()
    text = f"{document.title} {document.snippet} {url_path}".lower()
    editorial_terms = [
        "best",
        "top",
        "compare",
        "comparison",
        "guide",
        "tested",
        "review",
        "alternatives",
        "/blog/",
        "/library/",
        "/resources/",
        "/tools/",
        "/news/",
        "/article/",
        "/blog",
    ]
    return any(term in text for term in editorial_terms)


def _looks_vendor_like(document: SourceDocument) -> bool:
    text = f"{document.title} {document.snippet} {document.content[:1500]}".lower()
    vendor_terms = [
        "pricing",
        "contact sales",
        "book demo",
        "request demo",
        "integrations",
        "features",
        "platform",
        "product",
        "customers",
        "enterprise",
        "get started",
        "free trial",
        "use cases",
    ]
    return any(term in text for term in vendor_terms)


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
        key = (signal["label"], signal["source_url"])
        unique[key] = signal
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
