from dataclasses import asdict, dataclass, field
from typing import Dict, List

from fund_llm.agents.base import score_to_stance
from fund_llm.agents.chief_agent import _score_to_rating
from fund_llm.contracts import FinalAnalysisResult, FundAnalysisInput
from fund_llm.feature_builder import FeatureBuilder

CORE_AGENT_NAMES = [
    "PerformanceAgent",
    "ExposureAgent",
    "RiskAgent",
    "SentimentAgent",
    "SectorAgent",
]


@dataclass
class EvaluationCheck:
    name: str
    passed: bool
    severity: str
    score_awarded: int
    max_score: int
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class EvaluationReport:
    request_id: str
    overall_status: str
    total_score: int
    max_score: int
    passed_checks: int
    failed_checks: int
    checks: List[EvaluationCheck]
    summary: str
    manual_review_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _joined_text(values: List[str]) -> str:
    return " ".join(value for value in values if value).lower()


def _strings_from_result(result: FinalAnalysisResult) -> List[str]:
    texts = list(result.key_thesis) + list(result.main_risks) + list(result.action_plan) + [result.summary]
    for output in result.agent_outputs:
        texts.extend(output.key_points)
        texts.extend(output.risks)
        texts.extend(output.recommendations)
        texts.append(output.narrative)
    return [text for text in texts if text]


def _make_check(
    name: str,
    passed_units: int,
    total_units: int,
    max_score: int,
    severity: str,
    details: List[str],
) -> EvaluationCheck:
    total_units = max(total_units, 1)
    score_awarded = round((passed_units / total_units) * max_score)
    return EvaluationCheck(
        name=name,
        passed=passed_units == total_units,
        severity=severity,
        score_awarded=score_awarded,
        max_score=max_score,
        details=details,
    )


def evaluate_analysis_result(payload: FundAnalysisInput, result: FinalAnalysisResult) -> EvaluationReport:
    features = FeatureBuilder().build(payload)
    checks: List[EvaluationCheck] = []
    result_texts = _strings_from_result(result)
    joined_result_text = _joined_text(result_texts)
    outputs_by_name = {output.agent_name: output for output in result.agent_outputs}

    required_top_level = {
        "overall_rating": bool(result.overall_rating),
        "overall_score": result.overall_score is not None,
        "key_thesis": bool(result.key_thesis),
        "main_risks": bool(result.main_risks),
        "action_plan": bool(result.action_plan),
        "agent_outputs": bool(result.agent_outputs),
        "summary": bool(result.summary),
    }
    structure_details = [
        f"Missing or empty top-level field: {field_name}"
        for field_name, field_ok in required_top_level.items()
        if not field_ok
    ]
    structure_passed_units = len(required_top_level) - len(structure_details)
    for agent_name in CORE_AGENT_NAMES:
        if agent_name not in outputs_by_name:
            structure_details.extend(
                [
                    f"Missing core agent output: {agent_name}",
                    f"{agent_name} is missing a score because the agent output is absent.",
                    f"{agent_name} is missing narrative/key points because the agent output is absent.",
                ]
            )
            continue
        output = outputs_by_name[agent_name]
        if output.status == "success":
            if output.score is None:
                structure_details.append(f"{agent_name} is successful but has no score.")
            else:
                structure_passed_units += 1
            if not output.key_points:
                structure_details.append(f"{agent_name} is successful but has no key points.")
            else:
                structure_passed_units += 1
            if not output.narrative:
                structure_details.append(f"{agent_name} is successful but has no narrative.")
            else:
                structure_passed_units += 1
        else:
            structure_passed_units += 3
    structure_total_units = len(required_top_level) + len(CORE_AGENT_NAMES) * 3
    checks.append(
        _make_check(
            name="structure_completeness",
            passed_units=structure_passed_units,
            total_units=structure_total_units,
            max_score=20,
            severity="high",
            details=structure_details or ["Top-level result structure looks complete."],
        )
    )

    score_consistency_total = 2 + len([output for output in result.agent_outputs if output.status == "success"])
    score_consistency_passed = 0
    score_consistency_details = []

    expected_rating = _score_to_rating(result.overall_score)
    if result.overall_rating == expected_rating:
        score_consistency_passed += 1
    else:
        score_consistency_details.append(
            f"overall_rating={result.overall_rating} does not match overall_score={result.overall_score:.2f}."
        )

    success_count = len([output for output in result.agent_outputs if output.status == "success"])
    error_count = len(result.agent_outputs) - success_count
    metadata_success = result.metadata.get("success_agent_count")
    metadata_error = result.metadata.get("error_agent_count")
    if metadata_success == str(success_count) and metadata_error == str(error_count):
        score_consistency_passed += 1
    else:
        score_consistency_details.append(
            "metadata success/error agent counts do not match actual agent outputs."
        )

    for output in result.agent_outputs:
        if output.status != "success" or output.score is None:
            continue
        expected_stance = score_to_stance(output.score)
        if output.stance == expected_stance:
            score_consistency_passed += 1
        else:
            score_consistency_details.append(
                f"{output.agent_name} stance={output.stance} does not match score={output.score:.2f}."
            )

    checks.append(
        _make_check(
            name="score_consistency",
            passed_units=score_consistency_passed,
            total_units=score_consistency_total,
            max_score=15,
            severity="high",
            details=score_consistency_details or ["Scores, ratings, and stances are aligned."],
        )
    )

    coverage_details = []
    coverage_passed = 0
    for agent_name in CORE_AGENT_NAMES:
        if agent_name in outputs_by_name:
            coverage_passed += 1
        else:
            coverage_details.append(f"Core agent missing from output: {agent_name}")
    checks.append(
        _make_check(
            name="core_agent_coverage",
            passed_units=coverage_passed,
            total_units=len(CORE_AGENT_NAMES),
            max_score=15,
            severity="high",
            details=coverage_details or ["All current core agents are represented."],
        )
    )

    evidence_items = []
    performance_output = outputs_by_name.get("PerformanceAgent")
    if performance_output:
        evidence_items.append(
            any("total return" in point.lower() for point in performance_output.key_points)
        )
        evidence_items.append(
            any("max drawdown" in point.lower() for point in performance_output.key_points)
        )
    else:
        evidence_items.extend([False, False])

    if features.data_quality_flags.get("has_benchmark"):
        evidence_items.append("benchmark" in joined_result_text or "excess return" in joined_result_text)
    if features.data_quality_flags.get("has_news_signal"):
        evidence_items.append("SentimentAgent" in outputs_by_name and result.metadata.get("has_news_signal") == "true")
    if features.data_quality_flags.get("has_industry_exposure"):
        evidence_items.append("SectorAgent" in outputs_by_name and result.metadata.get("has_sector_context") == "true")

    evidence_passed = sum(1 for item in evidence_items if item)
    evidence_details = []
    if performance_output and not any("total return" in point.lower() for point in performance_output.key_points):
        evidence_details.append("PerformanceAgent key points do not explicitly mention total return.")
    if performance_output and not any("max drawdown" in point.lower() for point in performance_output.key_points):
        evidence_details.append("PerformanceAgent key points do not explicitly mention max drawdown.")
    if features.data_quality_flags.get("has_benchmark") and not (
        "benchmark" in joined_result_text or "excess return" in joined_result_text
    ):
        evidence_details.append("Benchmark-aware input did not produce benchmark or excess-return references.")
    if features.data_quality_flags.get("has_news_signal") and result.metadata.get("has_news_signal") != "true":
        evidence_details.append("News-aware input did not propagate sentiment coverage metadata.")
    if features.data_quality_flags.get("has_industry_exposure") and result.metadata.get("has_sector_context") != "true":
        evidence_details.append("Industry-aware input did not propagate sector coverage metadata.")
    checks.append(
        _make_check(
            name="evidence_coverage",
            passed_units=evidence_passed,
            total_units=len(evidence_items),
            max_score=20,
            severity="medium",
            details=evidence_details or ["Key evidence signals are reflected in the output."],
        )
    )

    missing_data_total = 0
    missing_data_passed = 0
    missing_data_details = []
    if not features.data_quality_flags.get("has_benchmark"):
        missing_data_total += 1
        if result.metadata.get("has_benchmark") == "false" and "benchmark" in _joined_text(result.main_risks):
            missing_data_passed += 1
        else:
            missing_data_details.append("Missing benchmark context was not clearly surfaced in final risks/metadata.")
    if not features.data_quality_flags.get("has_news_signal"):
        missing_data_total += 1
        if result.metadata.get("has_news_signal") == "false" and "news" in _joined_text(result.main_risks):
            missing_data_passed += 1
        else:
            missing_data_details.append("Missing news context was not clearly surfaced in final risks/metadata.")
    if not features.data_quality_flags.get("has_industry_exposure"):
        missing_data_total += 1
        if result.metadata.get("has_sector_context") == "false" and "sector" in _joined_text(result.main_risks):
            missing_data_passed += 1
        else:
            missing_data_details.append("Missing sector context was not clearly surfaced in final risks/metadata.")
    if missing_data_total == 0:
        missing_data_total = 1
        missing_data_passed = 1
        missing_data_details = ["Missing-data downgrade rules were not triggered for this case."]
    checks.append(
        _make_check(
            name="missing_data_handling",
            passed_units=missing_data_passed,
            total_units=missing_data_total,
            max_score=10,
            severity="medium",
            details=missing_data_details,
        )
    )

    risk_profile = features.extra_context.get("client_risk_profile", "")
    risk_profile_total = 1
    risk_profile_passed = 1
    risk_profile_details = ["Risk-profile-specific guidance was not required for this case."]
    if risk_profile:
        risk_profile_details = []
        risk_profile_passed = 0
        if risk_profile.lower() in _joined_text(result.action_plan + result.key_thesis + result.main_risks):
            risk_profile_passed = 1
        else:
            risk_profile_details.append(
                f"Client risk profile '{risk_profile}' was not reflected in final guidance."
            )
    checks.append(
        _make_check(
            name="risk_profile_alignment",
            passed_units=risk_profile_passed,
            total_units=risk_profile_total,
            max_score=10,
            severity="medium",
            details=risk_profile_details or ["Client risk profile is reflected in final guidance."],
        )
    )

    sanity_total = len([output for output in result.agent_outputs if output.status == "success"]) + 1
    sanity_passed = 0
    sanity_details = []
    if result.summary and result.summary != "API returned empty response":
        sanity_passed += 1
    else:
        sanity_details.append("Top-level summary is empty or an API fallback string.")
    for output in result.agent_outputs:
        if output.status != "success":
            continue
        if output.narrative and output.narrative != "API returned empty response" and " failed:" not in output.narrative:
            sanity_passed += 1
        else:
            sanity_details.append(f"{output.agent_name} narrative looks empty or failed.")
    checks.append(
        _make_check(
            name="narrative_sanity",
            passed_units=sanity_passed,
            total_units=sanity_total,
            max_score=10,
            severity="low",
            details=sanity_details or ["Narratives are present and do not look obviously broken."],
        )
    )

    total_score = sum(check.score_awarded for check in checks)
    max_score = sum(check.max_score for check in checks)
    failed_checks = len([check for check in checks if not check.passed])
    high_severity_failures = len([check for check in checks if not check.passed and check.severity == "high"])

    if total_score >= 85 and high_severity_failures == 0:
        overall_status = "pass"
    elif total_score >= 60:
        overall_status = "review"
    else:
        overall_status = "fail"

    summary = (
        f"Automated LLM evaluation scored {total_score}/{max_score}. "
        f"Status={overall_status}. Failed checks={failed_checks}."
    )

    manual_review_items = [
        "Check whether narratives overstate unsupported time windows or benchmark claims.",
        "Check whether sector and sentiment interpretations match the actual holdings and recent events.",
        "Check whether the final recommendation feels appropriate for the stated client risk profile.",
    ]

    return EvaluationReport(
        request_id=result.request_id,
        overall_status=overall_status,
        total_score=total_score,
        max_score=max_score,
        passed_checks=len(checks) - failed_checks,
        failed_checks=failed_checks,
        checks=checks,
        summary=summary,
        manual_review_items=manual_review_items,
    )
