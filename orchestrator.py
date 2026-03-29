from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from workflows.research_workflow import build_research_workflow
from utils.formatters import write_csv, write_summary
from utils.schemas import InvestigationRecord


@dataclass
class PipelineResult:
    leads: List[InvestigationRecord]
    csv_path: Path
    summary_path: Path
    json_path: Path


def run_pipeline(query: str, output_dir: Path) -> PipelineResult:
    graph = build_research_workflow()
    state = graph.invoke({"query": query, "trace": []})
    brief = state["brief"]
    leads: List[InvestigationRecord] = state.get("investigation_records", [])

    for line in state.get("trace", []):
        print(line)

    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"output_{run_id}.csv"
    summary_path = output_dir / f"summary_{run_id}.md"
    json_path = output_dir / f"result_{run_id}.json"

    write_csv(csv_path, leads, brief)
    write_summary(summary_path, leads, brief)
    from utils.formatters import write_json
    write_json(json_path, leads, brief)

    return PipelineResult(leads=leads, csv_path=csv_path, summary_path=summary_path, json_path=json_path)
