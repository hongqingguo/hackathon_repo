# Hackathon Multi-Agent Research Copilot

This repo contains a LangGraph-based research workflow that separates:

- `agents/` for decision-making nodes
- `skills/` for deterministic state transformations
- `tools/` for low-level capabilities
- `state/` for typed workflow state
- `workflows/` for graph assembly

Current runtime supports generalized entity investigation across `company`, `person`, and `product` examples using tool-backed search, evidence extraction, reasoning, validation, and scoring.

If `OPENAI_API_KEY` is set, the planner and reasoner can use `langchain-openai` for structured LLM-backed planning and evidence interpretation. If no key is set, the workflow falls back to deterministic local logic.

Run:

```bash
python main.py "Compare products in San Francisco about pricing and integrations"
```

Outputs are written to `output/output.csv` and `output/summary.md`.
