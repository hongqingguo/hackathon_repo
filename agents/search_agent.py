from typing import List

from tools.search_provider_llm import (
    add_cross_domain_documents,
    build_candidate_entity,
    discover_search_urls,
    expand_first_party_documents,
    fetch_root_document,
    fetch_source_document,
    infer_candidate_name,
    search_entities,
    select_canonical_document,
)
from utils.schemas import CandidateEntity, SearchBrief


class SearchAgent:
    def run(self, brief: SearchBrief) -> List[CandidateEntity]:
        if brief.search_backend == "mock":
            return search_entities(brief)

        urls = discover_search_urls(brief)
        candidates: List[CandidateEntity] = []
        seen_domains: set[str] = set()

        for url in urls[:12]:
            primary_document = fetch_source_document(url)
            if not primary_document or primary_document.domain in seen_domains:
                continue

            root_document = fetch_root_document(primary_document)
            first_party_documents = expand_first_party_documents(brief, primary_document, root_document)
            canonical_document = select_canonical_document(brief, first_party_documents)
            if not canonical_document or canonical_document.domain in seen_domains:
                continue

            candidate_name = infer_candidate_name(brief, canonical_document)
            source_documents = add_cross_domain_documents(
                brief=brief,
                candidate_name=candidate_name,
                canonical_document=canonical_document,
                source_documents=first_party_documents,
            )
            candidates.append(
                build_candidate_entity(
                    brief=brief,
                    candidate_name=candidate_name,
                    canonical_document=canonical_document,
                    primary_document=primary_document,
                    source_documents=source_documents,
                )
            )
            seen_domains.add(canonical_document.domain)

        return candidates
