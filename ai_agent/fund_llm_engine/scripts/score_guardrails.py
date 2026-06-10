from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any
from urllib import error, request


PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DEFAULT_AGENT_URL = "http://127.0.0.1:5003/api/ai/fund/analyze"
DEFAULT_FUNDS = ["000001", "512100", "003358"]
STABLE_AGENTS = {"PerformanceAgent", "RiskAgent", "SentimentAgent"}
DATA_SENSITIVE_AGENTS = {"ExposureAgent", "BondExposureAgent", "SectorAgent"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or compare stable AI score snapshots for FundMasterAI demos."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot = subparsers.add_parser("snapshot", help="Call the Agent API and write a compact score snapshot.")
    snapshot.add_argument("--agent-url", default=DEFAULT_AGENT_URL)
    snapshot.add_argument("--fund", action="append", dest="funds", help="Fund code to include. Can be repeated.")
    snapshot.add_argument("--start-date", default="2025/01/01")
    snapshot.add_argument("--risk-profile", default="balanced")
    snapshot.add_argument("--output", required=True)
    snapshot.add_argument("--real-llm", action="store_true", help="Use real LLM mode. Default is mock mode.")
    snapshot.add_argument("--timeout", type=int, default=180)

    compare = subparsers.add_parser("compare", help="Compare two score snapshots.")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.add_argument("--output")
    compare.add_argument("--fail-on-unexpected", action="store_true")
    compare.add_argument("--score-tolerance", type=float, default=0.05)
    compare.add_argument("--stable-agent-tolerance", type=float, default=0.50)

    scope = subparsers.add_parser("scope-check", help="Check git changes against team ownership boundaries.")
    scope.add_argument("--repo-root", default=os.path.abspath(os.path.join(PROJECT_ROOT, "..", "..")))
    scope.add_argument("--allow-backend", action="store_true")
    scope.add_argument("--output")

    return parser.parse_args(argv[1:])


def read_json(path: str) -> dict[str, Any]:
    with open(os.path.abspath(path), "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(payload: dict[str, Any], output_path: str | None) -> int:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if output_path:
        output_path = os.path.abspath(output_path)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(rendered)
            file.write("\n")
        print(f"Wrote guardrail report to {output_path}", file=sys.stderr)
        return 0
    print(rendered)
    return 0


def post_json(url: str, body: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Agent API returned HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Agent API is not reachable at {url}: {exc.reason}") from exc
    if payload.get("code") != 200:
        raise RuntimeError(f"Agent API failed for {body.get('code')}: {payload.get('message')}")
    return payload


def compact_agent_output(output: dict[str, Any]) -> dict[str, Any]:
    score = output.get("score")
    return {
        "agent_name": output.get("agent_name"),
        "status": output.get("status"),
        "stance": output.get("stance"),
        "score": round(float(score), 4) if score is not None else None,
        "confidence": round(float(output.get("confidence") or 0.0), 4),
    }


def trace_summary(trace: list[dict[str, Any]]) -> dict[str, Any]:
    titles = {item.get("title"): item for item in trace if isinstance(item, dict)}
    tools = titles.get("Discovered backend tools", {}).get("evidence", {})
    coverage = titles.get("Checked backend data coverage", {}).get("evidence", {})
    return {
        "available_tool_count": tools.get("available_tool_count"),
        "successful_tool_count": tools.get("successful_tool_count"),
        "errored_tool_count": tools.get("errored_tool_count"),
        "missing_or_limited": coverage.get("missing_or_limited", {}),
    }


def compact_result(api_payload: dict[str, Any], request_body: dict[str, Any]) -> dict[str, Any]:
    data = api_payload["data"]
    coverage = api_payload.get("coverage", {})
    agent_outputs = [compact_agent_output(item) for item in data.get("agent_outputs", [])]
    return {
        "fund_code": request_body["code"],
        "start_date": request_body["start_date"],
        "mock": request_body["mock"],
        "overall_score": round(float(data.get("overall_score") or 0.0), 4),
        "overall_rating": data.get("overall_rating"),
        "missing_fields": sorted(data.get("missing_fields") or []),
        "agent_outputs": agent_outputs,
        "coverage": {
            "data_coverage": coverage.get("data_coverage", {}),
            "nav_points": coverage.get("nav_points"),
            "fund_name": coverage.get("fund_name"),
            "fund_type": coverage.get("fund_type"),
            "normalized_fund_type": coverage.get("normalized_fund_type"),
            "fund_family": coverage.get("fund_family"),
        },
        "analysis_trace": trace_summary(data.get("analysis_trace") or []),
    }


def run_snapshot(args: argparse.Namespace) -> int:
    funds = args.funds or DEFAULT_FUNDS
    results = []
    for fund_code in funds:
        body = {
            "code": fund_code,
            "start_date": args.start_date,
            "client_risk_profile": args.risk_profile,
            "mock": not args.real_llm,
            "max_nav_points": 260,
            "max_parallel_agents": 3 if args.real_llm else 6,
            "llm_timeout_seconds": args.timeout,
        }
        api_payload = post_json(args.agent_url, body, args.timeout)
        results.append(compact_result(api_payload, body))

    snapshot = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agent_url": args.agent_url,
        "funds": results,
    }
    return write_json(snapshot, args.output)


def indexed_agents(fund: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("agent_name")): item
        for item in fund.get("agent_outputs", [])
        if item.get("agent_name")
    }


def score_delta(before: Any, after: Any) -> float | None:
    if before is None or after is None:
        return None
    return round(float(after) - float(before), 4)


def classify_agent_change(
    agent_name: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    tolerance: float,
) -> str:
    if before is None or after is None:
        return "needs_explanation"
    if before.get("status") != after.get("status"):
        return "expected_data_change" if agent_name in DATA_SENSITIVE_AGENTS else "needs_explanation"
    delta = score_delta(before.get("score"), after.get("score"))
    if delta is None or abs(delta) <= tolerance:
        return "stable"
    if agent_name in DATA_SENSITIVE_AGENTS:
        return "expected_data_change"
    if agent_name in STABLE_AGENTS:
        return "unexpected"
    return "needs_explanation"


def compare_fund(before: dict[str, Any], after: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    before_agents = indexed_agents(before)
    after_agents = indexed_agents(after)
    agent_names = sorted(set(before_agents) | set(after_agents))
    agent_changes = []
    classifications = set()
    for name in agent_names:
        before_agent = before_agents.get(name)
        after_agent = after_agents.get(name)
        classification = classify_agent_change(
            name,
            before_agent,
            after_agent,
            args.stable_agent_tolerance,
        )
        classifications.add(classification)
        agent_changes.append(
            {
                "agent_name": name,
                "classification": classification,
                "before_status": before_agent.get("status") if before_agent else None,
                "after_status": after_agent.get("status") if after_agent else None,
                "before_score": before_agent.get("score") if before_agent else None,
                "after_score": after_agent.get("score") if after_agent else None,
                "score_delta": score_delta(
                    before_agent.get("score") if before_agent else None,
                    after_agent.get("score") if after_agent else None,
                ),
            }
        )

    before_coverage = before.get("coverage", {}).get("data_coverage", {})
    after_coverage = after.get("coverage", {}).get("data_coverage", {})
    coverage_changed = before_coverage != after_coverage
    before_agent_count = len(before_agents)
    after_agent_count = len(after_agents)
    overall_delta = score_delta(before.get("overall_score"), after.get("overall_score"))
    overall_classification = "stable"
    if before_agent_count != after_agent_count:
        overall_classification = "needs_explanation"
    elif overall_delta is not None and abs(overall_delta) > args.score_tolerance:
        overall_classification = "expected_data_change" if coverage_changed else "needs_explanation"

    if "unexpected" in classifications:
        status = "fail"
    elif "needs_explanation" in classifications or overall_classification == "needs_explanation":
        status = "review"
    else:
        status = "pass"

    return {
        "fund_code": after.get("fund_code"),
        "status": status,
        "overall": {
            "classification": overall_classification,
            "before_score": before.get("overall_score"),
            "after_score": after.get("overall_score"),
            "score_delta": overall_delta,
            "before_rating": before.get("overall_rating"),
            "after_rating": after.get("overall_rating"),
            "before_agent_count": before_agent_count,
            "after_agent_count": after_agent_count,
        },
        "coverage_changed": coverage_changed,
        "before_missing_fields": before.get("missing_fields", []),
        "after_missing_fields": after.get("missing_fields", []),
        "agent_changes": agent_changes,
    }


def run_compare(args: argparse.Namespace) -> int:
    before = read_json(args.before)
    after = read_json(args.after)
    before_funds = {item["fund_code"]: item for item in before.get("funds", [])}
    after_funds = {item["fund_code"]: item for item in after.get("funds", [])}
    missing_in_after = sorted(set(before_funds) - set(after_funds))
    missing_in_before = sorted(set(after_funds) - set(before_funds))
    comparisons = [
        compare_fund(before_funds[fund_code], after_funds[fund_code], args)
        for fund_code in sorted(set(before_funds) & set(after_funds))
    ]
    report_status = "pass"
    if missing_in_after or missing_in_before:
        report_status = "review"
    if any(item["status"] == "fail" for item in comparisons):
        report_status = "fail"
    elif any(item["status"] == "review" for item in comparisons):
        report_status = "review"

    report = {
        "schema_version": 1,
        "status": report_status,
        "before": os.path.abspath(args.before),
        "after": os.path.abspath(args.after),
        "missing_in_after": missing_in_after,
        "missing_in_before": missing_in_before,
        "comparisons": comparisons,
    }
    write_json(report, args.output)
    return 1 if args.fail_on_unexpected and report_status == "fail" else 0


def changed_files(repo_root: str) -> list[str]:
    command = ["git", "-C", repo_root, "status", "--short", "--untracked-files=all"]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    files = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def run_scope_check(args: argparse.Namespace) -> int:
    repo_root = os.path.abspath(args.repo_root)
    files = changed_files(repo_root)
    backend_changes = [path for path in files if path.startswith("backend/")]
    status = "pass"
    message = "No backend changes detected."
    if backend_changes and not args.allow_backend:
        status = "fail"
        message = "Backend changes detected. AI guardrails default to backend read-only."
    elif backend_changes:
        status = "review"
        message = "Backend changes are allowed by override; document why they are needed."
    report = {
        "schema_version": 1,
        "status": status,
        "repo_root": repo_root,
        "changed_files": files,
        "backend_changes": backend_changes,
        "message": message,
    }
    write_json(report, args.output)
    return 1 if status == "fail" else 0


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.command == "snapshot":
            return run_snapshot(args)
        if args.command == "compare":
            return run_compare(args)
        if args.command == "scope-check":
            return run_scope_check(args)
    except (OSError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"score_guardrails failed: {exc}", file=sys.stderr)
        return 1
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
