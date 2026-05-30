import json
import os
from dataclasses import asdict, dataclass, field
from typing import Dict, List

from fund_llm.contracts import FinalAnalysisResult, FundAnalysisInput
from fund_llm.evaluation import EvaluationReport, evaluate_analysis_result
from fund_llm.mock_pipeline import run_mock_analysis_for_input
from fund_llm.real_pipeline import run_real_analysis_for_input

STATUS_RANK = {
    "fail": 0,
    "review": 1,
    "pass": 2,
}


@dataclass
class GoldenCaseCheck:
    name: str
    passed: bool
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class GoldenCaseReport:
    case_id: str
    tier: str
    description: str
    input_path: str
    notes_path: str | None
    analysis_mode: str
    overall_status: str
    evaluation_status: str
    evaluation_score: int
    evaluation_max_score: int
    checks: List[GoldenCaseCheck]
    manual_review_items: List[str]
    result_path: str | None = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class GoldenSuiteReport:
    manifest_path: str
    analysis_mode: str
    overall_status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_reports: List[GoldenCaseReport]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _load_manifest(manifest_path: str) -> Dict[str, object]:
    with open(manifest_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _load_input(input_path: str) -> FundAnalysisInput:
    with open(input_path, "r", encoding="utf-8") as file:
        return FundAnalysisInput.from_dict(json.load(file))


def _run_analysis(payload: FundAnalysisInput, mode: str, max_parallel_agents: int | None = None):
    if mode == "real":
        return run_real_analysis_for_input(payload, max_parallel_agents=max_parallel_agents)
    return run_mock_analysis_for_input(payload, max_parallel_agents=max_parallel_agents)


def _relative_path(workspace_root: str, absolute_path: str | None) -> str | None:
    if not absolute_path:
        return None
    return os.path.relpath(absolute_path, workspace_root)


def _resolve_output_dir(workspace_root: str, output_dir: str | None) -> str | None:
    if not output_dir:
        return None
    if os.path.isabs(output_dir):
        return os.path.abspath(output_dir)
    return os.path.abspath(os.path.join(workspace_root, output_dir))


def _write_case_result(
    results_dir: str,
    case_id: str,
    analysis_mode: str,
    result: FinalAnalysisResult,
) -> str:
    os.makedirs(results_dir, exist_ok=True)
    result_path = os.path.join(results_dir, f"{case_id}_{analysis_mode}_result.json")
    with open(result_path, "w", encoding="utf-8") as file:
        json.dump(result.to_dict(), file, ensure_ascii=False, indent=2)
        file.write("\n")
    return result_path


def _check_required_agents(required_agents: List[str], result_agent_names: List[str]) -> GoldenCaseCheck:
    missing_agents = [agent_name for agent_name in required_agents if agent_name not in result_agent_names]
    return GoldenCaseCheck(
        name="required_agents",
        passed=not missing_agents,
        details=missing_agents or ["All required agents are present."],
    )


def _check_expected_metadata(expected_metadata: Dict[str, str], actual_metadata: Dict[str, str]) -> GoldenCaseCheck:
    mismatches = []
    for key, expected_value in expected_metadata.items():
        actual_value = actual_metadata.get(key)
        if str(actual_value) != str(expected_value):
            mismatches.append(f"{key}: expected {expected_value}, got {actual_value}")
    return GoldenCaseCheck(
        name="expected_metadata",
        passed=not mismatches,
        details=mismatches or ["Metadata expectations matched."],
    )


def _check_expected_missing_fields(expected_missing_fields: List[str], actual_missing_fields: List[str]) -> GoldenCaseCheck:
    missing_expectations = [
        field_name for field_name in expected_missing_fields if field_name not in actual_missing_fields
    ]
    return GoldenCaseCheck(
        name="expected_missing_fields",
        passed=not missing_expectations,
        details=missing_expectations or ["Missing-field expectations matched."],
    )


def _result_text(result: FinalAnalysisResult) -> str:
    fragments = []
    fragments.extend(result.key_thesis)
    fragments.extend(result.main_risks)
    fragments.extend(result.action_plan)
    fragments.append(result.summary)
    for output in result.agent_outputs:
        fragments.extend(output.key_points)
        fragments.extend(output.risks)
        fragments.extend(output.recommendations)
        fragments.append(output.narrative)
    return "\n".join(fragment for fragment in fragments if fragment)


def _check_expected_text_fragments(expected_fragments: List[str], result: FinalAnalysisResult) -> GoldenCaseCheck:
    result_text = _result_text(result).lower()
    missing_fragments = [
        fragment for fragment in expected_fragments if fragment.lower() not in result_text
    ]
    return GoldenCaseCheck(
        name="expected_text_fragments",
        passed=not missing_fragments,
        details=missing_fragments or ["Expected text fragments were found in the result."],
    )


def _check_minimum_status(minimum_status: str, evaluation_report: EvaluationReport) -> GoldenCaseCheck:
    actual_rank = STATUS_RANK.get(evaluation_report.overall_status, -1)
    minimum_rank = STATUS_RANK.get(minimum_status, -1)
    passed = actual_rank >= minimum_rank
    details = (
        [f"Evaluation status {evaluation_report.overall_status} is below required {minimum_status}."]
        if not passed
        else [f"Evaluation status {evaluation_report.overall_status} met required {minimum_status}."]
    )
    return GoldenCaseCheck(name="minimum_evaluation_status", passed=passed, details=details)


def run_golden_suite(
    manifest_path: str,
    analysis_mode: str = "mock",
    max_parallel_agents: int | None = None,
    results_dir: str | None = None,
) -> GoldenSuiteReport:
    manifest_path = os.path.abspath(manifest_path)
    workspace_root = os.path.dirname(os.path.dirname(manifest_path))
    resolved_results_dir = _resolve_output_dir(workspace_root, results_dir)
    manifest = _load_manifest(manifest_path)
    case_reports: List[GoldenCaseReport] = []

    for case in manifest.get("cases", []):
        input_path = os.path.abspath(os.path.join(workspace_root, case["input_path"]))
        notes_path = case.get("notes_path")
        if notes_path:
            notes_path = os.path.abspath(os.path.join(workspace_root, notes_path))

        payload = _load_input(input_path)
        result = _run_analysis(payload, analysis_mode, max_parallel_agents=max_parallel_agents)
        result_path = None
        if resolved_results_dir:
            result_path = _write_case_result(resolved_results_dir, case["case_id"], analysis_mode, result)
        evaluation_report = evaluate_analysis_result(payload, result)
        expectations = case.get("expectations", {})
        result_agent_names = [output.agent_name for output in result.agent_outputs]

        checks = [
            _check_minimum_status(expectations.get("minimum_evaluation_status", "review"), evaluation_report),
            _check_required_agents(expectations.get("required_agents", []), result_agent_names),
            _check_expected_metadata(expectations.get("expected_metadata", {}), result.metadata),
            _check_expected_missing_fields(
                expectations.get("expected_missing_fields", []),
                result.missing_fields,
            ),
        ]
        if expectations.get("expected_text_fragments"):
            checks.append(
                _check_expected_text_fragments(
                    expectations.get("expected_text_fragments", []),
                    result,
                )
            )

        overall_status = "pass" if all(check.passed for check in checks) else "review"
        if not checks[0].passed or not checks[1].passed:
            overall_status = "fail"

        case_reports.append(
            GoldenCaseReport(
                case_id=case["case_id"],
                tier=case["tier"],
                description=case["description"],
                input_path=_relative_path(workspace_root, input_path) or case["input_path"],
                notes_path=_relative_path(workspace_root, notes_path),
                analysis_mode=analysis_mode,
                overall_status=overall_status,
                evaluation_status=evaluation_report.overall_status,
                evaluation_score=evaluation_report.total_score,
                evaluation_max_score=evaluation_report.max_score,
                checks=checks,
                manual_review_items=evaluation_report.manual_review_items,
                result_path=_relative_path(workspace_root, result_path),
            )
        )

    passed_cases = len([report for report in case_reports if report.overall_status == "pass"])
    failed_cases = len([report for report in case_reports if report.overall_status == "fail"])
    overall_status = "pass"
    if failed_cases:
        overall_status = "fail"
    elif passed_cases != len(case_reports):
        overall_status = "review"

    return GoldenSuiteReport(
        manifest_path=_relative_path(workspace_root, manifest_path) or manifest_path,
        analysis_mode=analysis_mode,
        overall_status=overall_status,
        total_cases=len(case_reports),
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        case_reports=case_reports,
    )
