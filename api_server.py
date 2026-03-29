from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel, Field

from orchestrator import run_pipeline
from utils.formatters import build_result_payload


app = FastAPI(
    title="Hackathon Multi-Agent Research Copilot API",
    version="0.1.0",
    description="Lightweight API wrapper around the LangGraph investigation workflow.",
)


class InvestigateRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural-language investigation request.")
    output_dir: str = Field(default="output", description="Directory for run artifacts.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/capabilities")
def capabilities() -> dict:
    return {
        "entity_types": ["company", "person", "product"],
        "search_backends": ["mock", "live"],
        "outputs": ["csv", "markdown", "json"],
        "llm_nodes": ["planner", "reasoner"],
    }


@app.post("/investigate")
def investigate(request: InvestigateRequest) -> dict:
    result = run_pipeline(request.query, Path(request.output_dir))
    payload = build_result_payload(result.leads, result.brief)
    payload["artifacts"] = {
        "csv_path": str(result.csv_path),
        "summary_path": str(result.summary_path),
        "json_path": str(result.json_path),
    }
    return payload
