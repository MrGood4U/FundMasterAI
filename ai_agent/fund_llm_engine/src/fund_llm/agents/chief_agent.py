from statistics import mean

from fund_llm.agents.base import merge_lists
from fund_llm.contracts import AgentOutput, FinalAnalysisResult, FundFeaturePack


def _score_to_rating(score: float) -> str:
    if score >= 75:
        return "buy"
    if score >= 60:
        return "hold"
    if score >= 45:
        return "watch"
    return "avoid"


class ChiefAgent:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def aggregate(self, features: FundFeaturePack, agent_outputs: list[AgentOutput]) -> FinalAnalysisResult:
        successful_outputs = [
            output for output in agent_outputs if output.status == "success" and output.score is not None
        ]
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
            if output not in successful_outputs
            and output not in skipped_outputs
            and output not in not_applicable_outputs
        ]
        valid_scores = [output.score for output in successful_outputs if output.score is not None]
        confidence_outputs = [output for output in agent_outputs if output not in not_applicable_outputs]
        average_confidence = mean([output.confidence for output in confidence_outputs]) if confidence_outputs else 0.0

        overall_score = mean(valid_scores) if valid_scores else 0.0
        if error_outputs:
            overall_score = max(0.0, overall_score - (len(error_outputs) * 3))
        overall_score = round(overall_score, 2)
        overall_rating = _score_to_rating(overall_score)

        client_risk_profile = features.extra_context.get("client_risk_profile", "")
        chief_key_points = []
        if features.data_quality_flags.get("has_benchmark"):
            chief_key_points.append("Benchmark-relative context is available for cross-checking the agent views.")
        if features.data_quality_flags.get("has_news_signal"):
            chief_key_points.append("Recent news flow is available as an additional sentiment cross-check.")
        if features.data_quality_flags.get("has_industry_exposure"):
            chief_key_points.append("Sector exposure breakdown is available for industry-level cross-checking.")
        if not_applicable_outputs:
            chief_key_points.append(
                f"{len(not_applicable_outputs)} agent module(s) were not applicable to {features.normalized_fund_type}."
            )
        if features.fund_tags:
            chief_key_points.append(f"Fund role tags include {', '.join(features.fund_tags[:3])}.")
        if average_confidence >= 0.75:
            chief_key_points.append("Agent confidence is broadly solid under the current input coverage.")

        chief_risks = []
        if error_outputs:
            chief_risks.append("One or more agent modules failed, so the final view is only partial.")
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

        chief_actions = []
        if client_risk_profile:
            chief_actions.append(f"Match any allocation to a {client_risk_profile} risk profile.")
        if error_outputs:
            chief_actions.append("Re-run the analysis after the failed agent modules are restored.")
        if skipped_outputs:
            chief_actions.append("Do not treat skipped agent outputs as neutral signals; collect the missing data first.")
        if features.missing_fields:
            chief_actions.append("Fill the missing payload fields before making a higher-conviction decision.")

        key_thesis = merge_lists([chief_key_points] + [output.key_points for output in agent_outputs], limit=5)
        main_risks = merge_lists([chief_risks] + [output.risks for output in agent_outputs], limit=5)
        action_plan = merge_lists([chief_actions] + [output.recommendations for output in agent_outputs], limit=5)

        system_prompt = (
            "You are the chief fund advisor. Summarize the multi-agent findings into one final investment view. "
            "Write in English. Use only the supplied metrics, data quality flags, missing fields, and agent reports. "
            "Do not use outside knowledge about the fund, manager, holdings, sectors, or market narrative. "
            "If a field or agent is missing/skipped, state that it is unavailable instead of inferring it."
        )
        joined_reports = "\n\n".join(
            f"[{output.agent_name}] status={output.status}, score={output.score}, stance={output.stance}, confidence={output.confidence:.2f}\n{output.narrative}"
            for output in agent_outputs
        )
        user_prompt = (
            f"Fund: {features.fund_info.name} ({features.fund_info.code})\n"
            f"Normalized fund type: {features.normalized_fund_type}\n"
            f"Overall score: {overall_score:.2f}\n"
            f"Overall rating: {overall_rating}\n"
            f"Average agent confidence: {average_confidence:.2f}\n"
            f"Error agent count: {len(error_outputs)}\n"
            f"Fund tags: {features.fund_tags}\n"
            f"Client risk profile: {client_risk_profile}\n"
            f"Data quality flags: {features.data_quality_flags}\n"
            f"Data coverage: {features.data_coverage}\n"
            f"Missing fields: {features.missing_fields}\n"
            f"Key thesis candidates: {key_thesis}\n"
            f"Risk candidates: {main_risks}\n"
            f"Action plan candidates: {action_plan}\n\n"
            f"Agent reports:\n{joined_reports}\n\n"
            "Please write a concise final summary."
        )
        summary = self.llm_client.chat(system_prompt, user_prompt)

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
            "news_item_count": str(features.data_quality_metrics.get("news_item_count", 0)),
            "client_risk_profile": client_risk_profile,
            "agent_health": "healthy" if not error_outputs and not skipped_outputs else "partial",
            "fund_tags": ",".join(features.fund_tags[:3]),
        }
        for key, value in features.data_coverage.items():
            metadata[f"coverage_{key}"] = value

        return FinalAnalysisResult(
            request_id=features.request_id,
            overall_rating=overall_rating,
            overall_score=overall_score,
            key_thesis=key_thesis,
            main_risks=main_risks,
            action_plan=action_plan,
            agent_outputs=agent_outputs,
            summary=summary,
            missing_fields=features.missing_fields,
            metadata=metadata,
        )
