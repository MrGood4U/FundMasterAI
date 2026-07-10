from dataclasses import asdict, dataclass, field
from typing import Dict, List

from fund_llm import config
from fund_llm.agents.base import score_to_stance
from fund_llm.agents.chief_agent import _score_to_rating
from fund_llm.contracts import FinalAnalysisResult, FundAnalysisInput
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.rating_policy import assess_rating_coverage

CORE_AGENT_NAMES = [
    "PerformanceAgent",
    "ExposureAgent",
    "BondExposureAgent",
    "RiskAgent",
    "SentimentAgent",
    "SectorAgent",
    "MarketAgent",
]

RATED_RATINGS = {"buy", "hold", "watch", "avoid"}
VALID_ANALYSIS_STATUSES = {"complete", "partial", "insufficient_data", "technical_error"}
VALID_SKIPPED_STANCES = {"insufficient_data", "not_applicable"}


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
    texts = (
        list(result.key_thesis)
        + list(result.main_risks)
        + list(result.action_plan)
        + [result.summary, result.score_explanation]
    )
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


def _make_gate(
    name: str,
    passed: bool,
    severity: str,
    details: List[str],
) -> EvaluationCheck:
    """Build a non-scoring gate that can cap or fail the final evaluation."""

    return EvaluationCheck(
        name=name,
        passed=passed,
        severity=severity,
        score_awarded=0,
        max_score=0,
        details=details,
    )


def _classify_agent_execution(features, agent_outputs):
    successful = []
    insufficient_data = []
    not_applicable = []
    technical_errors = []
    invalid = []

    for output in agent_outputs:
        if output.status == "success":
            successful.append(output)
            continue

        if output.status == "error":
            technical_errors.append(output)
            continue

        if output.status != "skipped":
            invalid.append(f"{output.agent_name} has unsupported status={output.status!r}.")
            continue

        if output.score is not None:
            invalid.append(f"{output.agent_name} is skipped but still has score={output.score}.")
            continue
        if output.stance not in VALID_SKIPPED_STANCES:
            invalid.append(
                f"{output.agent_name} is skipped with unsupported stance={output.stance!r}."
            )
            continue
        if output.stance == "insufficient_data":
            insufficient_data.append(output)
            continue

        not_applicable.append(output)

    return {
        "successful": successful,
        "insufficient_data": insufficient_data,
        "not_applicable": not_applicable,
        "technical_errors": technical_errors,
        "invalid": invalid,
    }


def evaluate_analysis_result(payload: FundAnalysisInput, result: FinalAnalysisResult) -> EvaluationReport:
    features = FeatureBuilder().build(payload)
    checks: List[EvaluationCheck] = []
    result_texts = _strings_from_result(result)
    joined_result_text = _joined_text(result_texts)
    outputs_by_name = {output.agent_name: output for output in result.agent_outputs}
    analysis_status = result.metadata.get("analysis_status", "complete")
    execution = _classify_agent_execution(features, result.agent_outputs)
    rating_coverage = assess_rating_coverage(features, result.agent_outputs)

    required_top_level = {
        "overall_rating": bool(result.overall_rating),
        "overall_score": (
            result.overall_score is not None
            or analysis_status in {"insufficient_data", "technical_error"}
        ),
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
        elif (
            output.status == "skipped"
            and output.stance in VALID_SKIPPED_STANCES
            and output.score is None
        ):
            structure_passed_units += 3
        elif output.status == "error":
            structure_details.extend(
                [
                    f"{agent_name} ended in a technical error.",
                    f"{agent_name} has no usable score because execution failed.",
                    f"{agent_name} error output cannot satisfy normal narrative completeness.",
                ]
            )
        else:
            structure_details.extend(
                [
                    f"{agent_name} has an invalid status/score/stance combination.",
                    f"{agent_name} does not provide a usable score.",
                    f"{agent_name} does not satisfy the agent output contract.",
                ]
            )
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

    technical_error_count = len(execution["technical_errors"])
    successful_count = rating_coverage.scored_count
    applicable_count = rating_coverage.applicable_count
    valid_score_ratio = rating_coverage.ratio
    missing_core_agents = list(rating_coverage.missing_core_agent_names)
    rating_quorum = rating_coverage.quorum_met
    coverage_has_issues = bool(rating_coverage.policy_issue_agent_names)
    rated_decision = (
        result.overall_rating in RATED_RATINGS
        and result.overall_score is not None
    )
    valid_abstention = (
        analysis_status == "insufficient_data"
        and result.overall_rating == "insufficient_data"
        and result.overall_score is None
        and not execution["technical_errors"]
        and not execution["invalid"]
    )
    no_usable_score_failure = successful_count == 0 and not valid_abstention
    critical_execution_failure = (
        bool(execution["invalid"])
        or no_usable_score_failure
        or (
            technical_error_count > 0
            and technical_error_count * 2 > max(applicable_count, 1)
        )
    )
    execution_health_passed = (
        not execution["technical_errors"]
        and not execution["invalid"]
        and not no_usable_score_failure
        and not coverage_has_issues
    )
    execution_details = []
    if execution["technical_errors"]:
        execution_details.append(
            "Technical agent errors: "
            + ", ".join(output.agent_name for output in execution["technical_errors"])
        )
    execution_details.extend(execution["invalid"])
    if rating_coverage.missing_agent_names:
        execution_details.append(
            "Missing expected agent outputs: "
            + ", ".join(rating_coverage.missing_agent_names)
        )
    if rating_coverage.duplicate_agent_names:
        execution_details.append(
            "Duplicate agent outputs excluded from rating coverage: "
            + ", ".join(rating_coverage.duplicate_agent_names)
        )
    if rating_coverage.invalid_agent_names:
        execution_details.append(
            "Invalid scoring outputs excluded from rating coverage: "
            + ", ".join(rating_coverage.invalid_agent_names)
        )
    if rating_coverage.unexpected_active_agent_names:
        execution_details.append(
            "Unexpected active outputs for routed-out agents: "
            + ", ".join(rating_coverage.unexpected_active_agent_names)
        )
    if no_usable_score_failure:
        execution_details.append(
            "No usable successful agent score is available and the result is not a valid abstention."
        )
    if not execution_details:
        execution_details.append(
            "Agent execution is healthy; legitimate insufficient-data and not-applicable skips are allowed."
        )
    checks.append(
        _make_gate(
            name="agent_execution_health",
            passed=execution_health_passed,
            severity="critical" if critical_execution_failure else "high",
            details=execution_details,
        )
    )

    nav_point_count = features.data_quality_metrics.get("nav_point_count", 0)
    low_sample = nav_point_count < config.MIN_NAV_POINTS_FOR_RATING
    analysis_status_valid = analysis_status in VALID_ANALYSIS_STATUSES
    rated_without_quorum = rated_decision and not rating_quorum
    invalid_partial = analysis_status == "partial" and not (
        rated_decision and rating_quorum
    )
    decision_eligibility_passed = (
        analysis_status_valid
        and (not low_sample or valid_abstention)
        and not rated_without_quorum
        and not invalid_partial
    )
    decision_eligibility_details = []
    if not analysis_status_valid:
        decision_eligibility_details.append(
            f"Unsupported analysis_status={analysis_status!r}."
        )
    if low_sample and not valid_abstention:
        decision_eligibility_details.append(
            f"NAV sample has {nav_point_count} point(s), below the "
            f"{config.MIN_NAV_POINTS_FOR_RATING}-point rating floor; the result must abstain with "
            "analysis_status=insufficient_data, overall_rating=insufficient_data, and overall_score=None."
        )
    if rated_without_quorum:
        quorum_failures = []
        if missing_core_agents:
            quorum_failures.append(
                "core agent(s) not successful: " + ", ".join(missing_core_agents)
            )
        if successful_count < 3:
            quorum_failures.append(
                f"only {successful_count} valid score(s); at least "
                f"{config.MIN_RATING_AGENT_COUNT} are required"
            )
        if not rating_coverage.meets_ratio:
            quorum_failures.append(
                f"valid-score coverage is {valid_score_ratio:.2%} "
                f"({successful_count}/{applicable_count}); at least "
                f"{config.MIN_RATING_COVERAGE_RATIO:.0%} is required"
            )
        decision_eligibility_details.append(
            "A directional rating was published without aggregation quorum: "
            + "; ".join(quorum_failures)
            + "."
        )
    if invalid_partial and not rated_without_quorum:
        decision_eligibility_details.append(
            "analysis_status='partial' requires a four-tier rating, a non-null score, "
            "successful PerformanceAgent and RiskAgent outputs, at least "
            f"{config.MIN_RATING_AGENT_COUNT} valid scores, and at least "
            f"{config.MIN_RATING_COVERAGE_RATIO:.0%} valid-score coverage."
        )
    if not decision_eligibility_details:
        decision_eligibility_details.append(
            "The final decision respects the minimum NAV sample and abstention policy."
        )
    checks.append(
        _make_gate(
            name="decision_eligibility",
            passed=decision_eligibility_passed,
            severity="critical",
            details=decision_eligibility_details,
        )
    )

    score_consistency_total = 2 + len(
        [output for output in result.agent_outputs if output.status == "success"]
    )
    score_consistency_passed = 0
    score_consistency_details = []

    expected_rating = None
    decision_is_consistent = False
    if analysis_status == "complete":
        if result.overall_score is not None and result.overall_rating in RATED_RATINGS:
            expected_rating = _score_to_rating(result.overall_score)
            decision_is_consistent = (
                result.overall_rating == expected_rating
                and not execution["technical_errors"]
                and not coverage_has_issues
            )
    elif analysis_status == "partial":
        if result.overall_score is not None and result.overall_rating in RATED_RATINGS:
            expected_rating = _score_to_rating(result.overall_score)
            decision_is_consistent = (
                result.overall_rating == expected_rating and rating_quorum
            )
    elif analysis_status == "insufficient_data":
        expected_rating = "insufficient_data"
        decision_is_consistent = (
            result.overall_rating == expected_rating and result.overall_score is None
        )
    elif analysis_status == "technical_error":
        expected_rating = "unavailable"
        decision_is_consistent = (
            result.overall_rating == expected_rating and result.overall_score is None
        )

    if decision_is_consistent:
        score_consistency_passed += 1
    else:
        score_consistency_details.append(
            "Final decision fields are inconsistent: "
            f"analysis_status={analysis_status!r}, overall_rating={result.overall_rating!r}, "
            f"overall_score={result.overall_score!r}, expected_rating={expected_rating!r}."
        )

    success_count = len([output for output in result.agent_outputs if output.status == "success"])
    error_count = len([output for output in result.agent_outputs if output.status == "error"])
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
    if features.data_quality_flags.get("has_bond_holdings") or features.data_quality_flags.get("has_asset_allocation"):
        evidence_items.append("BondExposureAgent" in outputs_by_name and result.metadata.get("has_bond_exposure") == "true")

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
    if (
        (features.data_quality_flags.get("has_bond_holdings") or features.data_quality_flags.get("has_asset_allocation"))
        and result.metadata.get("has_bond_exposure") != "true"
    ):
        evidence_details.append("Bond-aware input did not propagate fixed-income exposure metadata.")
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
    if (
        features.data_quality_flags.get("bond_exposure_applicable", False)
        and not features.data_quality_flags.get("has_bond_holdings")
        and not features.data_quality_flags.get("has_asset_allocation")
    ):
        missing_data_total += 1
        if result.metadata.get("has_bond_exposure") == "false" and "bond" in _joined_text(result.main_risks):
            missing_data_passed += 1
        else:
            missing_data_details.append("Missing bond exposure context was not clearly surfaced in final risks/metadata.")
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
    critical_failures = len(
        [check for check in checks if not check.passed and check.severity == "critical"]
    )
    high_severity_failures = len(
        [check for check in checks if not check.passed and check.severity == "high"]
    )

    if critical_failures:
        overall_status = "fail"
    elif total_score >= 85 and high_severity_failures == 0:
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
