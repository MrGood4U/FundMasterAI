from fund_llm.agents.base import BaseAgent, clamp, data_driven_confidence, score_to_stance
from fund_llm.contracts import AgentOutput, FundFeaturePack

EXCESS_RETURN_ALERT_THRESHOLD = 0.005


class PerformanceAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "PerformanceAgent"

    def analyze(self, features: FundFeaturePack) -> AgentOutput:
        total_return = features.return_metrics.get("total_return", 0.0)
        return_3m = features.return_metrics.get("return_3m")
        return_6m = features.return_metrics.get("return_6m")
        return_1y = features.return_metrics.get("return_1y")
        max_drawdown = features.risk_metrics.get("max_drawdown", 0.0)
        excess_return = features.benchmark_metrics.get("excess_return")
        excess_return_3m = features.benchmark_metrics.get("excess_return_3m")
        excess_return_1y = features.benchmark_metrics.get("excess_return_1y")
        available_window_count = features.data_quality_metrics.get("available_return_window_count", 0)

        raw_score = 58 + (total_return * 180) + (max_drawdown * 30)
        if return_3m is not None:
            raw_score += return_3m * 80
        if return_6m is not None:
            raw_score += return_6m * 70
        if return_1y is not None:
            raw_score += return_1y * 60
        if excess_return is not None:
            raw_score += excess_return * 120
        if excess_return_3m is not None:
            raw_score += excess_return_3m * 80
        if excess_return_1y is not None:
            raw_score += excess_return_1y * 60
        if available_window_count == 0:
            raw_score -= 6
        score = clamp(raw_score)
        stance = score_to_stance(score)

        system_prompt = (
            "You are a professional fund performance analyst. Explain the fund's recent performance using only "
            "the provided metrics. Do not infer holdings, sectors, manager behavior, or market causes from outside knowledge."
        )
        user_prompt = (
            f"Fund: {features.fund_info.name} ({features.fund_info.code})\n"
            f"Asset type: {features.fund_info.asset_type}\n"
            f"Total return: {total_return:.4f}\n"
            f"3M return: {return_3m}\n"
            f"6M return: {return_6m}\n"
            f"1Y return: {return_1y}\n"
            f"Excess return: {excess_return}\n"
            f"3M excess return: {excess_return_3m}\n"
            f"1Y excess return: {excess_return_1y}\n"
            f"Max drawdown: {max_drawdown:.4f}\n"
            f"Data quality flags: {features.data_quality_flags}\n"
            f"Missing fields: {features.missing_fields}\n"
            "Please explain the performance in concise investment language."
        )
        narrative = self.llm_client.chat(system_prompt, user_prompt)

        key_points = [
            f"Total return is {total_return:.2%}.",
            f"Max drawdown is {max_drawdown:.2%}.",
        ]
        if return_3m is not None:
            key_points.append(f"3-month return is {return_3m:.2%}.")
        if return_1y is not None:
            key_points.append(f"1-year return is {return_1y:.2%}.")
        if excess_return_1y is not None:
            key_points.append(f"1-year excess return versus benchmark is {excess_return_1y:.2%}.")
        elif excess_return is not None:
            key_points.append(f"Sample excess return versus benchmark is {excess_return:.2%}.")

        risks = []
        if max_drawdown < -0.15:
            risks.append("Historical drawdown is meaningful and should be watched.")
        if excess_return_3m is not None and excess_return_3m < -EXCESS_RETURN_ALERT_THRESHOLD:
            risks.append("Recent performance has lagged the benchmark over the last 3 months.")
        if excess_return_1y is not None and excess_return_1y < -EXCESS_RETURN_ALERT_THRESHOLD:
            risks.append("Longer-horizon excess return versus the benchmark is still negative.")
        if available_window_count < 2:
            risks.append("Available return history is still limited for a fuller trend read.")

        recommendations = ["Review the fund as a medium-term holding candidate."]
        if total_return < 0:
            recommendations = ["Avoid chasing the fund before confirming a clearer recovery."]
        elif excess_return_1y is not None and excess_return_1y > EXCESS_RETURN_ALERT_THRESHOLD:
            recommendations = ["Relative performance versus the benchmark looks constructive for continued tracking."]
        elif available_window_count < 2:
            recommendations = ["Wait for a longer performance history before making a stronger conviction call."]

        return AgentOutput(
            agent_name=self.name,
            status="success",
            score=score,
            stance=stance,
            key_points=key_points,
            risks=risks,
            recommendations=recommendations,
            confidence=data_driven_confidence(features),
            narrative=narrative,
        )
