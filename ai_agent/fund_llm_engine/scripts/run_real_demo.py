import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fund_llm.contracts import FundAnalysisInput
from fund_llm.mock_pipeline import build_mock_input
from fund_llm.real_pipeline import run_real_analysis_for_input


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the real-model fund analysis demo.")
    parser.add_argument("input_path", nargs="?", help="Optional path to an input JSON file.")
    parser.add_argument(
        "--max-parallel-agents",
        type=int,
        default=None,
        help="Optional cap for concurrent specialist agents.",
    )
    parser.add_argument("--model", dest="model", help="Optional LLM model override for this run.")
    parser.add_argument("--output", dest="output_path", help="Optional path to write the result JSON file.")
    return parser.parse_args(argv[1:])


def load_input(input_path: str | None) -> FundAnalysisInput:
    if not input_path:
        return build_mock_input()

    input_path = os.path.abspath(input_path)
    with open(input_path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    return FundAnalysisInput.from_dict(payload)


def emit_result(result: dict, output_path: str | None) -> int:
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        output_path = os.path.abspath(output_path)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(rendered)
            file.write("\n")
        print(f"Wrote analysis result to {output_path}", file=sys.stderr)
        return 0
    print(rendered)
    return 0


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    payload = load_input(args.input_path)
    try:
        result = run_real_analysis_for_input(
            payload,
            model=args.model,
            max_parallel_agents=args.max_parallel_agents,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"run_real_demo failed: {exc}", file=sys.stderr)
        return 1
    return emit_result(result.to_dict(), args.output_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
