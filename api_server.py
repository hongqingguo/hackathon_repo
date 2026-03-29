from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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
    search_backend: str = Field(
        default="",
        description="Optional backend override: mock, live, or tavily.",
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path("static") / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/capabilities")
def capabilities() -> dict:
    return {
        "entity_types": ["company", "person", "product"],
        "search_backends": ["mock", "live", "tavily"],
        "outputs": ["csv", "markdown", "json"],
        "llm_nodes": ["planner", "reasoner"],
        "review_support": True,
        "ui": True,
    }


@app.post("/investigate")
def investigate(request: InvestigateRequest) -> dict:
    try:
        output_dir = Path(request.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid output_dir: {exc}") from exc

    try:
        result = run_pipeline(
            request.query,
            output_dir,
            search_backend_override=request.search_backend,
        )
        payload = build_result_payload(result.leads, result.brief, trace=result.trace)
        payload["artifacts"] = {
            "csv_path": str(result.csv_path),
            "summary_path": str(result.summary_path),
            "json_path": str(result.json_path),
        }
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Investigation failed: {exc}") from exc
