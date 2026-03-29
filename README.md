# Hackathon Multi-Agent Research Copilot

This repo contains a LangGraph-based research workflow that separates:

- `agents/` for decision-making nodes
- `skills/` for deterministic state transformations
- `tools/` for low-level capabilities
- `state/` for typed workflow state
- `workflows/` for graph assembly

Current runtime supports generalized entity investigation across `company`, `person`, and `product` examples using tool-backed search, evidence extraction, reasoning, validation, and scoring.

Run:

```bash
python main.py "Compare products in San Francisco about pricing and integrations"
```

Outputs are written to `output/output.csv` and `output/summary.md`.
