# Hackathon Multi-Agent Research Copilot

This repo contains a LangGraph-based research workflow for generalized investigation across `company`, `person`, and `product` entities.

## Architecture

The codebase is intentionally split into production-friendly layers:

- `agents/` for decision-making nodes
- `skills/` for deterministic state transformations
- `tools/` for low-level capabilities
- `state/` for typed workflow state
- `workflows/` for graph assembly

Current workflow:

1. planner
2. research
3. extract
4. qualify
5. reason
6. validate
7. score
8. format

## Current Status

- `Phase 1`: complete
- `Phase 2`: in progress
- `Phase 3`: started

Implemented today:

- LangGraph workflow orchestration
- typed graph state
- generalized entity model
- source-backed evidence extraction
- fallback reasoning for missing facts
- domain-aware validation logic
- lightweight human-review flags and review queue output
- structured LLM planner and reasoner with deterministic fallback
- paired CSV/Markdown plus JSON output artifacts
- live search with richer same-domain page fetching
- provider-backed search options: `mock`, `live`, and `tavily`
- FastAPI layer with `/`, `/health`, `/capabilities`, and `/investigate`
- thin browser UI for running the workflow without the CLI

Still pending:

- deeper source reputation scoring
- stronger live-page semantic extraction beyond heuristic normalization
- auth/background jobs if the API is productized

If `OPENAI_API_KEY` is set, the planner and reasoner can use `langchain-openai` for structured LLM-backed planning and evidence interpretation. If no key is set, the workflow falls back to deterministic local logic.

The search layer is also provider-based:

- `SEARCH_BACKEND=mock` uses the built-in sample dataset
- `SEARCH_BACKEND=live` uses a lightweight live ingestion path built on DuckDuckGo HTML search plus page fetching and heuristic normalization

This makes the path from hackathon MVP to production clearer without changing the workflow contract.

## Environment

Recommended environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL=gpt-4o-mini`
- `OPENAI_TEMPERATURE=0`
- `OPENAI_TIMEOUT=30`
- `OPENAI_MAX_RETRIES=2`
- `SEARCH_BACKEND=mock`
- `TAVILY_API_KEY` if you want API-backed production-style search

Run:

```bash
python main.py "Compare products in San Francisco about pricing and integrations"
```

Example additional runs:

```bash
python main.py "Find fintech startups in New York with CTO and signs they may need workflow automation"
python main.py "Compare people in New York about founder and technical budget influence"
```

Run the API:

```bash
uvicorn api_server:app --reload
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

## Outputs

Each run generates a matched pair:

- `output/output_<run_id>.csv`
- `output/summary_<run_id>.md`
- `output/result_<run_id>.json`

The API also returns the same result payload directly from `/investigate`.
The API returns:

- investigation metadata
- workflow trace
- ranked results
- artifact paths

CSV fields include:

- requested attribute
- best matching fact
- reasoning summary
- validation status
- validation scope
- validation sources
- human review flags
- source URLs

## Validation Semantics

Validation is intentionally domain-aware:

- repeated evidence from the same domain is treated as `same_domain_only`
- stronger corroboration requires multiple distinct domains
- conflicts are flagged separately from weak support

This keeps the system honest during demos and better aligned with production trust requirements.

## Limitations

Current limitations are explicit:

- `live` search still depends on public web pages and heuristic normalization
- `tavily` improves discovery quality but downstream page interpretation is still heuristic
- live extraction follows a small set of relevant same-domain pages, not full deep crawling
- LLM nodes depend on `OPENAI_API_KEY`
- validation is domain-aware but not yet source-reputation-aware
- API routes and the thin UI are lightweight wrappers around the workflow and do not yet include auth, background jobs, or async execution

## Next Step

The next planned milestone is improving semantic extraction quality and source reputation scoring while preserving the current graph, skills, and typed state contracts.
