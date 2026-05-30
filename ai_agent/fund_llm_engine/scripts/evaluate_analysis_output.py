import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fund_llm.contracts import FinalAnalysisResult, FundAnalysisInput
from fund_llm.evaluation import evaluate_analysis_result
from fund_llm.mock_pipeline import build_mock_input, run_mock_analysis_for_input
from fund_llm.real_pipeline import run_real_analysis_for_input


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a fund analysis result with the project rubric.")
    parser.add_argument("--input", dest="input_path", help="Optional path to the input payload JSON.")
    parser.add_argument("--result", dest="result_path", help="Optional path to an existing result JSON.")
    parser.add_argument(
        "--mode",
        choices=["mock", "real"],
        default="mock",
        help="If --result is omitted, run mock or real analysis first before evaluating.",
    )
    parser.add_argument("--output", dest="output_path", help="Optional path to write the evaluation report JSON.")
    return parser.parse_args(argv[1:])


def load_input(input_path: str | None) -> FundAnalysisInput:
    if not input_path:
        return build_mock_input()
    with open(os.path.abspath(input_path), "r", encoding="utf-8") as file:
        return FundAnalysisInput.from_dict(json.load(file))


def load_or_run_result(payload: FundAnalysisInput, result_path: str | None, mode: str) -> FinalAnalysisResult:
    if result_path:
        with open(os.path.abspath(result_path), "r", encoding="utf-8") as file:
            return FinalAnalysisResult.from_dict(json.load(file))
    if mode == "real":
        return run_real_analysis_for_input(payload)
    return run_mock_analysis_for_input(payload)


def emit_report(report: dict, output_path: str | None) -> int:
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if output_path:
        output_path = os.path.abspath(output_path)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(rendered)
            file.write("\n")
        print(f"Wrote evaluation report to {output_path}", file=sys.stderr)
        return 0
    print(rendered)
    return 0


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    payload = load_input(args.input_path)
    try:
        result = load_or_run_result(payload, args.result_path, args.mode)
    except (RuntimeError, ValueError) as exc:
        print(f"evaluate_analysis_output failed: {exc}", file=sys.stderr)
        return 1

    report = evaluate_analysis_result(payload, result).to_dict()
    return emit_report(report, args.output_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
