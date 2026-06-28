import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fund_llm.golden_suite import run_golden_suite


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the project's golden-case suite.")
    parser.add_argument(
        "--manifest",
        default="examples/golden_cases_manifest.json",
        help="Path to the golden cases manifest JSON.",
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "real"],
        default="mock",
        help="Whether to run the suite through mock or real analysis.",
    )
    parser.add_argument(
        "--max-parallel-agents",
        type=int,
        default=None,
        help="Optional cap for concurrent specialist agents per case.",
    )
    parser.add_argument(
        "--include-results",
        action="store_true",
        help="Write each case's full analysis result JSON, including agent narratives.",
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        help="Directory for full case result JSON files. Implies --include-results.",
    )
    parser.add_argument("--output", dest="output_path", help="Optional path to write the suite report JSON.")
    return parser.parse_args(argv[1:])


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
        print(f"Wrote golden suite report to {output_path}", file=sys.stderr)
        return 0
    print(rendered)
    return 0


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    manifest_path = os.path.abspath(args.manifest)
    results_dir = args.results_dir
    if args.include_results and not results_dir:
        results_dir = "outputs/golden_case_results"
    try:
        report = run_golden_suite(
            manifest_path=manifest_path,
            analysis_mode=args.mode,
            max_parallel_agents=args.max_parallel_agents,
            results_dir=results_dir,
        ).to_dict()
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(f"run_golden_suite failed: {exc}", file=sys.stderr)
        return 1
    return emit_report(report, args.output_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
