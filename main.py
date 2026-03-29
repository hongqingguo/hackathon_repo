import sys
from pathlib import Path

from orchestrator import run_pipeline


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python main.py "Compare products in San Francisco about pricing and integrations"')
        return 1

    query = sys.argv[1]
    output_dir = Path("output")
    result = run_pipeline(query=query, output_dir=output_dir)

    print(f"Run completed for query: {query}")
    print(f"CSV saved to: {result.csv_path}")
    print(f"Summary saved to: {result.summary_path}")
    print(f"JSON saved to: {result.json_path}")
    print(f"Results found: {len(result.leads)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
