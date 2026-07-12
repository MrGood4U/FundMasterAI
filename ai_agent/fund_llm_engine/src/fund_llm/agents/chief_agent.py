from statistics import mean

from fund_llm import config
from fund_llm.agents.base import merge_lists
from fund_llm.contracts import AgentOutput, FinalAnalysisResult, FundFeaturePack
from fund_llm.rating_policy import assess_rating_coverage


INTERNAL_TAG_NAMES = {"backend-function-registry", "open-fund"}


def _display_fund_tags(features: FundFeaturePack) -> list[str]:
    internal = INTERNAL_TAG_NAMES | {features.normalized_fund_type, features.fund_family}
    return [tag for tag in features.fund_tags if tag and tag not in internal]


def _score_to_rating(score: float) -> str:
    if score >= 75:
        return "buy"
    if score >= 60:
        return "hold"
    if score >= 45:
        return "watch"
    return "avoid"


def _agent_display_name(agent_name: str) -> str:
    labels = {
        "PerformanceAgent": "Performance",
        "ExposureAgent": "Portfolio exposure",
        "BondExposureAgent": "Bond exposure",
        "RiskAgent": "Risk control",
        "SentimentAgent": "News signal",
        "SectorAgent": "Sector context",
        "MarketAgent": "Peer/market context",
    }
    return labels.get(agent_name, agent_name)


def _score_contribution_phrase(score: float) -> str:
    if score >= 75:
        return "strongly supports the rating"
    if score >= 60:
        return "supports the rating"
    if score >= 45:
        return "keeps the view mixed"
    return "pulls the rating down"


def _build_score_explanation(
    overall_rating: str,
    overall_score: float,
    successful_outputs: list[AgentOutput],
    skipped_outputs: list[AgentOutput],
    not_applicable_outputs: list[AgentOutput],
    error_outputs: list[AgentOutput],
    applicable_count: int,
) -> str:
    if not successful_outputs:
        return (
            "No successful specialist scores were available, so the final rating has low conviction. "
            "Review missing or failed agent outputs before using the recommendation."
        )

    score_items = []
    drag_items = []
    support_items = []
    for output in successful_outputs:
        if output.score is None:
            continue
        label = _agent_display_name(output.agent_name)
        score_items.append(f"{label} scored {output.score:.1f} and {_score_contribution_phrase(output.score)}")
        if output.score < 45:
            drag_items.append(f"{label} ({output.score:.1f})")
        elif output.score >= 75:
            support_items.append(f"{label} ({output.score:.1f})")

    explanation = (
        f"The {overall_rating.upper()} rating comes from the current average of "
        f"{len(successful_outputs)} successful specialist score(s), resulting in {overall_score:.1f}/100. "
        f"{'; '.join(score_items)}."
    )

    if applicable_count:
        explanation += (
            f" Rating coverage is {len(successful_outputs)}/{applicable_count} applicable specialist modules."
        )

    if drag_items and support_items:
        explanation += (
            f" Strong contributors such as {', '.join(support_items)} are offset by weaker signals from "
            f"{', '.join(drag_items)}, which is why the rating is not higher."
        )
    elif drag_items:
        explanation += f" The rating is held back by weaker signals from {', '.join(drag_items)}."
    elif support_items and overall_rating != "buy":
        explanation += (
            f" {', '.join(support_items)} supports the view, but the remaining specialist scores keep "
            "the final rating below the BUY range."
        )

    if skipped_outputs:
        explanation += (
            f" {len(skipped_outputs)} specialist module(s) were skipped because required data was unavailable; "
            "they are not treated as neutral scores."
        )
    if not_applicable_outputs:
        explanation += (
            f" {len(not_applicable_outputs)} module(s) were marked not applicable for this fund type."
        )
    if error_outputs:
        explanation += (
            f" {len(error_outputs)} module(s) failed and were excluded from financial scoring."
        )

    return explanation


def _build_abstention_explanation(
    overall_rating: str,
    blockers: list[str],
) -> str:
    reason_text = "; ".join(blockers) if blockers else "rating eligibility requirements were not met"
    if overall_rating == "unavailable":
        return (
            "No investment rating or overall score was published because a technical specialist failure "
            f"made the aggregation incomplete: {reason_text}. Technical availability is not treated as "
            "positive or negative investment evidence."
        )
    return (
        "No investment rating or overall score was published because the available evidence was "
        f"insufficient: {reason_text}. The system abstains instead of mapping missing evidence to "
        "BUY, HOLD, WATCH, or AVOID."
    )


def _summary_looks_incomplete(summary: str) -> bool:
    text = (summary or "").strip()
    if not text:
        return True
    if len(text.split()) < 25:
        return True
    return text[-1] not in ".!?"


def _build_fallback_summary(
    features: FundFeaturePack,
    overall_rating: str,
    overall_score: float,
    average_confidence: float,
    successful_outputs: list[AgentOutput],
    skipped_outputs: list[AgentOutput],
    error_outputs: list[AgentOutput],
) -> str:
    nav_points = features.data_quality_metrics.get("nav_point_count", 0)
    scored_outputs = [output for output in successful_outputs if output.score is not None]
    health_note = f"{len(scored_outputs)} specialist check(s) completed"
    if error_outputs:
        health_note = f"{len(error_outputs)} agent module(s) failed"
    elif skipped_outputs:
        health_note = f"{len(skipped_outputs)} agent module(s) were skipped because required data was unavailable"

    score_note = "No specialist score was available, so conviction is low."
    if scored_outputs:
        strongest = max(scored_outputs, key=lambda output: output.score or 0.0)
        weakest = min(scored_outputs, key=lambda output: output.score or 0.0)
        score_note = (
            f"The strongest signal is {_agent_display_name(strongest.agent_name)} "
            f"({strongest.score:.1f}/100), while the weakest is {_agent_display_name(weakest.agent_name)} "
            f"({weakest.score:.1f}/100)."
        )

    limitation_notes = []
    if features.missing_fields:
        limitation_notes.append(f"missing required payload fields: {', '.join(features.missing_fields[:4])}")
    if skipped_outputs:
        limitation_notes.append(f"{len(skipped_outputs)} specialist check(s) skipped because input data was unavailable")
    if error_outputs:
        limitation_notes.append(f"{len(error_outputs)} specialist check(s) failed")
    if limitation_notes:
        coverage_note = "Remaining limitations: " + "; ".join(limitation_notes) + "."
    else:
        coverage_note = "No required payload fields are missing under the currently integrated backend contract."

    return (
        f"{features.fund_info.name} ({features.fund_info.code}) receives a "
        f"{overall_rating.upper()} view with an overall score of {overall_score:.2f}/100, "
        f"based on {nav_points} NAV observations and backend function-registry data. "
        f"This is an evidence-based aggregation, not a direct prompt-only answer: {health_note}, "
        f"with average confidence of {average_confidence:.2f}. "
        f"{score_note} {coverage_note} "
        "Use this view as a decision aid and review the specialist evidence before making an allocation."
    )


def _build_abstention_summary(
    features: FundFeaturePack,
    overall_rating: str,
    blockers: list[str],
    successful_outputs: list[AgentOutput],
    skipped_outputs: list[AgentOutput],
    error_outputs: list[AgentOutput],
) -> str:
    nav_points = features.data_quality_metrics.get("nav_point_count", 0)
    reason_text = "; ".join(blockers) if blockers else "rating eligibility requirements were not met"
    if overall_rating == "unavailable":
        opening = "No investment rating was issued because the analysis is technically incomplete."
    else:
        opening = "No investment rating was issued because the available data is insufficient."
    return (
        f"{features.fund_info.name} ({features.fund_info.code}) was analysed with {nav_points} NAV observations. "
        f"{opening} The blocking reason is: {reason_text}. "
        f"{len(successful_outputs)} specialist score(s) completed, {len(skipped_outputs)} were skipped for "
        f"missing data, and {len(error_outputs)} failed technically. Collect the missing evidence or restore "
        "the failed module before using this analysis for an allocation decision."
    )


# 年化类指标需要足够长的净值历史才可靠。低于一年（约 252 个交易日）时，
# Sharpe / Calmar 等会被显著放大，因此随结果一起暴露样本量和可靠性标签，
# 让前端决定是否展示或加注，而不是直接把失真的数值当成可信结论。
QUANT_RELIABLE_MIN_POINTS = 252
QUANT_LIMITED_MIN_POINTS = 120


def _quant_metrics_reliability(nav_point_count: int) -> str:
    if nav_point_count >= QUANT_RELIABLE_MIN_POINTS:
        return "high"
    if nav_point_count >= QUANT_LIMITED_MIN_POINTS:
        return "medium"
    return "low"


def _build_quant_metrics(features: FundFeaturePack) -> dict:
    """Surface the NAV-only (A-class) quantitative metrics for the frontend.

    这些指标只依赖基金净值序列，对任何基金都成立，不需要个股交易记录。
    有基准时才附带超额收益（B 类指标），没有就不放，避免伪造。
    同时带上 sample_size（净值点数），让前端能判断年化指标是否基于足够样本。
    """
    return_metrics = features.return_metrics
    risk_metrics = features.risk_metrics
    nav_point_count = features.data_quality_metrics.get("nav_point_count", 0)
    if nav_point_count < config.MIN_NAV_POINTS_FOR_RATING:
        return {"sample_size": float(nav_point_count)}
    metrics = {
        "total_return": return_metrics.get("total_return", 0.0),
        "annualized_return": return_metrics.get("annualized_return", 0.0),
        "annualized_volatility": risk_metrics.get("annualized_volatility", 0.0),
        "max_drawdown": risk_metrics.get("max_drawdown", 0.0),
        "sharpe_ratio": risk_metrics.get("sharpe_ratio", 0.0),
        "sortino_ratio": risk_metrics.get("sortino_ratio", 0.0),
        "calmar_ratio": risk_metrics.get("calmar_ratio", 0.0),
        "positive_period_ratio": risk_metrics.get("positive_period_ratio", 0.0),
    }
    if "excess_return" in features.benchmark_metrics:
        metrics["excess_return"] = features.benchmark_metrics["excess_return"]
    rounded = {key: round(value, 6) for key, value in metrics.items()}
    rounded["sample_size"] = float(nav_point_count)
    return rounded


class ChiefAgent:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def aggregate(self, features: FundFeaturePack, agent_outputs: list[AgentOutput]) -> FinalAnalysisResult:
        rating_coverage = assess_rating_coverage(features, agent_outputs)
        successful_outputs = list(rating_coverage.valid_outputs)
        not_applicable_outputs = [
            output for output in agent_outputs if output.status == "skipped" and output.stance == "not_applicable"
        ]
        skipped_outputs = [
            output
            for output in agent_outputs
            if output.status == "skipped" and output not in not_applicable_outputs
        ]
        error_outputs = [
            output
            for output in agent_outputs
            if output.status == "error"
            or (
                output not in successful_outputs
                and output not in skipped_outputs
                and output not in not_applicable_outputs
            )
        ]
        valid_scores = [output.score for output in successful_outputs if output.score is not None]
        confidence_outputs = [output for output in agent_outputs if output not in not_applicable_outputs]
        average_confidence = mean([output.confidence for output in confidence_outputs]) if confidence_outputs else 0.0
        nav_point_count = features.data_quality_metrics.get("nav_point_count", 0)
        missing_core_agents = list(rating_coverage.missing_core_agent_names)
        applicable_output_count = rating_coverage.applicable_count
        scored_output_count = rating_coverage.scored_count
        rating_coverage_ratio = rating_coverage.ratio
        rating_policy_issue_names = list(rating_coverage.policy_issue_agent_names)
        rating_blockers = []
        if nav_point_count < config.MIN_NAV_POINTS_FOR_RATING:
            rating_blockers.append(
                f"{nav_point_count} NAV observations are below the minimum of "
                f"{config.MIN_NAV_POINTS_FOR_RATING}"
            )
        if missing_core_agents:
            rating_blockers.append(
                "required rating agents did not produce scores: " + ", ".join(missing_core_agents)
            )
        if scored_output_count < config.MIN_RATING_AGENT_COUNT:
            rating_blockers.append(
                f"{scored_output_count} scored specialist module(s) are below the minimum of "
                f"{config.MIN_RATING_AGENT_COUNT}"
            )
        if not rating_coverage.meets_ratio:
            rating_blockers.append(
                f"rating coverage {scored_output_count}/{applicable_output_count} "
                f"({rating_coverage_ratio:.0%}) is below the minimum of "
                f"{config.MIN_RATING_COVERAGE_RATIO:.0%}"
            )

        technical_coverage_issue = bool(error_outputs or rating_policy_issue_names)
        if nav_point_count < config.MIN_NAV_POINTS_FOR_RATING:
            analysis_status = "insufficient_data"
        elif rating_blockers:
            analysis_status = "technical_error" if technical_coverage_issue else "insufficient_data"
        elif technical_coverage_issue or skipped_outputs:
            analysis_status = "partial"
        else:
            analysis_status = "complete"

        rating_eligible = analysis_status in {"complete", "partial"} and bool(valid_scores)
        if rating_eligible:
            overall_score = round(mean(valid_scores), 2)
            overall_rating = _score_to_rating(overall_score)
            score_explanation = _build_score_explanation(
                overall_rating,
                overall_score,
                successful_outputs,
                skipped_outputs,
                not_applicable_outputs,
                error_outputs,
                applicable_output_count,
            )
        else:
            overall_score = None
            overall_rating = "unavailable" if analysis_status == "technical_error" else "insufficient_data"
            score_explanation = _build_abstention_explanation(overall_rating, rating_blockers)

        client_risk_profile = features.extra_context.get("client_risk_profile", "")
        display_fund_tags = _display_fund_tags(features)
        chief_key_points = []
        if features.data_quality_flags.get("has_benchmark"):
            chief_key_points.append("Benchmark-relative context is available for cross-checking the agent views.")
        if features.data_quality_flags.get("has_news_signal"):
            chief_key_points.append("Recent news flow is available as an additional sentiment cross-check.")
        if features.data_quality_flags.get("has_industry_exposure"):
            chief_key_points.append("Sector exposure breakdown is available for industry-level cross-checking.")
        if features.data_quality_flags.get("has_bond_holdings") or features.data_quality_flags.get("has_asset_allocation"):
            chief_key_points.append("Bond or asset-allocation exposure data is available for fixed-income cross-checking.")
        if not_applicable_outputs:
            chief_key_points.append(
                f"{len(not_applicable_outputs)} agent module(s) were not applicable to {features.normalized_fund_type}."
            )
        if display_fund_tags:
            chief_key_points.append(f"Fund role tags include {', '.join(display_fund_tags[:3])}.")
        if average_confidence >= 0.75:
            chief_key_points.append("Agent confidence is broadly solid under the current input coverage.")

        chief_risks = []
        if error_outputs:
            if rating_eligible:
                chief_risks.append(
                    f"{len(error_outputs)} specialist module(s) failed technically and were excluded; "
                    f"the rating uses the remaining {scored_output_count}/{applicable_output_count} applicable scores."
                )
            else:
                chief_risks.append(
                    "One or more agent modules failed technically and the remaining coverage was too low, "
                    "so no investment rating was published."
                )
        if rating_policy_issue_names:
            chief_risks.append(
                "Rating coverage has missing, duplicate, invalid, or routing-inconsistent Agent output(s): "
                + ", ".join(rating_policy_issue_names)
                + "."
            )
        if nav_point_count < config.MIN_NAV_POINTS_FOR_RATING:
            chief_risks.append(
                f"Only {nav_point_count} NAV observations were available; at least "
                f"{config.MIN_NAV_POINTS_FOR_RATING} are required before publishing a rating."
            )
        if missing_core_agents and nav_point_count >= config.MIN_NAV_POINTS_FOR_RATING:
            chief_risks.append(
                "Required performance/risk scoring coverage is incomplete, so the system abstained."
            )
        if skipped_outputs:
            chief_risks.append(
                f"{len(skipped_outputs)} agent module(s) were skipped because required input data was unavailable."
            )
        if features.missing_fields:
            chief_risks.append(
                f"Input is still missing {len(features.missing_fields)} field(s), which reduces analysis coverage."
            )
        if not features.data_quality_flags.get("has_benchmark"):
            chief_risks.append("No benchmark series was provided, so relative performance checks remain limited.")
        if not features.data_quality_flags.get("has_news_signal"):
            chief_risks.append("No recent news flow was provided, so event-driven sentiment context remains limited.")
        if (
            features.data_quality_flags.get("sector_analysis_applicable", True)
            and not features.data_quality_flags.get("has_industry_exposure")
        ):
            chief_risks.append("No industry exposure breakdown was provided, so sector-level context remains limited.")
        if (
            features.data_quality_flags.get("bond_exposure_applicable", False)
            and not features.data_quality_flags.get("has_bond_holdings")
            and not features.data_quality_flags.get("has_asset_allocation")
        ):
            chief_risks.append("No bond holdings or asset-allocation data was provided, so fixed-income exposure remains limited.")

        chief_actions = []
        if client_risk_profile:
            chief_actions.append(f"Match any allocation to a {client_risk_profile} risk profile.")
        if error_outputs:
            chief_actions.append("Re-run the analysis after the failed agent modules are restored.")
        if rating_policy_issue_names:
            chief_actions.append("Restore one valid output per expected Agent before relying on full coverage.")
        if nav_point_count < config.MIN_NAV_POINTS_FOR_RATING:
            chief_actions.append(
                f"Collect at least {config.MIN_NAV_POINTS_FOR_RATING} NAV observations before requesting an investment rating."
            )
        if skipped_outputs:
            chief_actions.append("Do not treat skipped agent outputs as neutral signals; collect the missing data first.")
        if features.missing_fields:
            chief_actions.append("Fill the missing payload fields before making a higher-conviction decision.")

        user_facing_outputs = [output for output in agent_outputs if output not in not_applicable_outputs]
        actionable_outputs = [output for output in user_facing_outputs if output.status != "error"]
        key_thesis = merge_lists(
            [chief_key_points] + [output.key_points for output in user_facing_outputs],
            limit=5,
        )
        main_risks = merge_lists(
            [chief_risks] + [output.risks for output in user_facing_outputs],
            limit=5,
        )
        action_plan = merge_lists(
            [chief_actions] + [output.recommendations for output in actionable_outputs],
            limit=5,
        )

        system_prompt = (
            "You are the chief fund advisor. Summarize the multi-agent findings into one final investment view. "
            "Respond in English only: even though fund names and data labels may be Chinese, "
            "the summary itself must be written in clear user-facing English. "
            "Use only the supplied metrics, data quality flags, missing fields, and agent reports. "
            "Do not use outside knowledge about the fund, manager, holdings, sectors, or market narrative. "
            "If a field or agent is missing/skipped, state that it is unavailable instead of inferring it. "
            "Do not describe zero missing fields as a limitation. "
            "Explain the main reason for the rating by naming the strongest and weakest specialist signals. "
            "Keep the final summary under 160 words and end with a complete sentence."
        )
        joined_reports = "\n\n".join(
            f"[{output.agent_name}] status={output.status}, score={output.score}, stance={output.stance}, confidence={output.confidence:.2f}\n{output.narrative}"
            for output in agent_outputs
        )
        overall_score_text = f"{overall_score:.2f}" if overall_score is not None else "not published"
        user_prompt = (
            f"Fund: {features.fund_info.name} ({features.fund_info.code})\n"
            f"Normalized fund type: {features.normalized_fund_type}\n"
            f"Overall score: {overall_score_text}\n"
            f"Overall rating: {overall_rating}\n"
            f"Analysis status: {analysis_status}\n"
            f"Rating coverage: {scored_output_count}/{applicable_output_count} "
            f"({rating_coverage_ratio:.0%})\n"
            f"Average agent confidence: {average_confidence:.2f}\n"
            f"Error agent count: {len(error_outputs)}\n"
            f"Fund tags: {display_fund_tags}\n"
            f"Client risk profile: {client_risk_profile}\n"
            f"Data quality flags: {features.data_quality_flags}\n"
            f"Data coverage: {features.data_coverage}\n"
            f"Missing fields: {features.missing_fields}\n"
            f"Key thesis candidates: {key_thesis}\n"
            f"Risk candidates: {main_risks}\n"
            f"Action plan candidates: {action_plan}\n\n"
            f"Agent reports:\n{joined_reports}\n\n"
            "Please write a concise final summary in two short paragraphs."
        )
        summary_source = "llm"
        if rating_eligible:
            try:
                # 7 个 agent 报告拼进 prompt 后较长，放宽输出预算，
                # 减少总评被截断而触发确定性回退的情况。
                summary = self.llm_client.chat(system_prompt, user_prompt, max_tokens=1100)
            except Exception:
                summary = ""
                summary_source = "deterministic_fallback"

            if (
                not getattr(self.llm_client, "is_mock", False)
                and _summary_looks_incomplete(summary)
            ):
                summary = _build_fallback_summary(
                    features,
                    overall_rating,
                    overall_score,
                    average_confidence,
                    successful_outputs,
                    skipped_outputs,
                    error_outputs,
                )
                summary_source = "deterministic_fallback"
        else:
            summary = _build_abstention_summary(
                features,
                overall_rating,
                rating_blockers,
                successful_outputs,
                skipped_outputs,
                error_outputs,
            )
            summary_source = "deterministic_abstention"

        specialist_narrative_fallback_count = len(
            [
                output
                for output in successful_outputs
                if output.metadata.get("narrative_source") == "deterministic_fallback"
            ]
        )
        if error_outputs or skipped_outputs or rating_policy_issue_names:
            agent_health = "partial"
        elif specialist_narrative_fallback_count:
            agent_health = "degraded"
        else:
            agent_health = "healthy"

        metadata = {
            "success_agent_count": str(len(successful_outputs)),
            "skipped_agent_count": str(len(skipped_outputs)),
            "not_applicable_agent_count": str(len(not_applicable_outputs)),
            "error_agent_count": str(len(error_outputs)),
            "average_confidence": f"{average_confidence:.2f}",
            "normalized_fund_type": features.normalized_fund_type,
            "fund_family": features.fund_family,
            "has_benchmark": str(features.data_quality_flags.get("has_benchmark", False)).lower(),
            "has_news_signal": str(features.data_quality_flags.get("has_news_signal", False)).lower(),
            "has_sector_context": str(features.data_quality_flags.get("has_industry_exposure", False)).lower(),
            "has_bond_exposure": str(
                features.data_quality_flags.get("has_bond_holdings", False)
                or features.data_quality_flags.get("has_asset_allocation", False)
            ).lower(),
            "news_item_count": str(features.data_quality_metrics.get("news_item_count", 0)),
            "client_risk_profile": client_risk_profile,
            "agent_health": agent_health,
            "analysis_status": analysis_status,
            "rating_eligible": str(rating_eligible).lower(),
            "rating_blockers": " | ".join(rating_blockers),
            "min_nav_points_for_rating": str(config.MIN_NAV_POINTS_FOR_RATING),
            "rating_scored_agent_count": str(scored_output_count),
            "rating_applicable_agent_count": str(applicable_output_count),
            "rating_coverage_ratio": f"{rating_coverage_ratio:.2f}",
            "rating_expected_agents": ",".join(rating_coverage.expected_agent_names),
            "rating_policy_issue_agents": ",".join(rating_policy_issue_names),
            "min_rating_agent_count": str(config.MIN_RATING_AGENT_COUNT),
            "min_rating_coverage_ratio": f"{config.MIN_RATING_COVERAGE_RATIO:.2f}",
            "specialist_narrative_fallback_count": str(specialist_narrative_fallback_count),
            "narrative_health": "fallback" if specialist_narrative_fallback_count else "llm",
            "fund_tags": ",".join(features.fund_tags[:3]),
            "summary_source": summary_source,
            "prompt_version": config.PROMPT_VERSION,
        }
        for key, value in features.data_coverage.items():
            metadata[f"coverage_{key}"] = value
        nav_point_count = features.data_quality_metrics.get("nav_point_count", 0)
        metadata["quant_metrics_sample_size"] = str(nav_point_count)
        metadata["quant_metrics_reliability"] = _quant_metrics_reliability(nav_point_count)

        return FinalAnalysisResult(
            request_id=features.request_id,
            overall_rating=overall_rating,
            overall_score=overall_score,
            key_thesis=key_thesis,
            main_risks=main_risks,
            action_plan=action_plan,
            agent_outputs=agent_outputs,
            summary=summary,
            score_explanation=score_explanation,
            missing_fields=features.missing_fields,
            metadata=metadata,
            quant_metrics=_build_quant_metrics(features),
        )
