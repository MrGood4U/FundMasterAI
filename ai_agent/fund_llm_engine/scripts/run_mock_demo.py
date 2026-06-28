import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fund_llm.contracts import FundAnalysisInput
from fund_llm.mock_pipeline import build_mock_input, run_mock_analysis_for_input


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the mock fund analysis demo.")
    parser.add_argument("input_path", nargs="?", help="Optional path to an input JSON file.")
    parser.add_argument("--output", dest="output_path", help="Optional path to write the result JSON file.")
    return parser.parse_args(argv[1:])


def load_input(input_path: str | None) -> FundAnalysisInput:
    if input_path:
        input_path = os.path.abspath(input_path)
        with open(input_path, "r", encoding="utf-8") as file:
            return FundAnalysisInput.from_dict(json.load(file))
    return build_mock_input()


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
    result = run_mock_analysis_for_input(payload).to_dict()
    return emit_result(result, args.output_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
