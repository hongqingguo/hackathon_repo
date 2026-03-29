import os
from typing import List, Optional
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup
from requests import Response

from utils.mock_data import MOCK_ENTITIES
from utils.schemas import CandidateEntity, SearchBrief, SourceDocument


def search_entities(brief: SearchBrief) -> List[CandidateEntity]:
    backend = os.getenv("SEARCH_BACKEND", "mock").strip().lower()
    if backend == "mock":
        return _search_mock_entities(brief)
    if backend == "live":
        return _search_live_entities(brief)
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


def _search_live_entities(brief: SearchBrief) -> List[CandidateEntity]:
    urls = _discover_urls(brief.search_queries or [brief.raw_query])
    candidates: List[CandidateEntity] = []
    for url in urls[:10]:
        document = _fetch_document(url)
        if not document:
            continue
        candidate = _candidate_from_document(brief, document)
        candidates.append(candidate)
    return candidates


def _discover_urls(search_queries: List[str]) -> List[str]:
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


def _candidate_from_document(brief: SearchBrief, document: SourceDocument) -> CandidateEntity:
    name = _infer_name_from_document(document)
    summary = document.snippet or document.content[:240]
    signals = _infer_signals(brief, document)
    facts = [
        {
            "field": "page_title",
            "value": document.title or name,
            "source_url": document.url,
            "snippet": document.snippet or document.content[:180],
        }
    ]
    if brief.subject:
        facts.append(
            {
                "field": "query_subject",
                "value": brief.subject,
                "source_url": document.url,
                "snippet": document.snippet or document.content[:180],
            }
        )

    return CandidateEntity(
        name=name,
        entity_type=brief.target_type,
        canonical_url=document.url,
        location=_infer_location(brief, document),
        summary=summary,
        tags=_infer_tags(brief, document),
        facts=facts,
        signals=signals,
        source_documents=[document],
    )


def _infer_name_from_document(document: SourceDocument) -> str:
    if document.title:
        return document.title.split("|")[0].split("-")[0].strip() or document.domain
    return document.domain


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


def _http_get(url: str) -> Response:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        return requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.ProxyError:
        session = requests.Session()
        session.trust_env = False
        return session.get(url, headers=headers, timeout=10)
