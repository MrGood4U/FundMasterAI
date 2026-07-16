from fund_llm import config
from fund_llm.agents.base import BaseAgent, clamp, data_driven_confidence, score_to_stance
from fund_llm.contracts import AgentOutput, FundFeaturePack


class RiskAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "RiskAgent"

    def analyze(self, features: FundFeaturePack) -> AgentOutput:
        nav_point_count = features.data_quality_metrics.get("nav_point_count", 0)
        if nav_point_count < config.MIN_NAV_POINTS_FOR_RATING:
            return AgentOutput(
                agent_name=self.name,
                status="skipped",
                score=None,
                stance="insufficient_data",
                key_points=[
                    f"Only {nav_point_count} NAV observation(s) are available; "
                    f"at least {config.MIN_NAV_POINTS_FOR_RATING} are required for risk scoring."
                ],
                risks=["Risk scoring was withheld because the NAV history is too short."],
                recommendations=[
                    f"Provide at least {config.MIN_NAV_POINTS_FOR_RATING} NAV observations before rating risk."
                ],
                confidence=0.0,
                narrative="Risk analysis skipped because the NAV history is insufficient for scoring.",
            )

        max_drawdown = features.risk_metrics.get("max_drawdown", 0.0)
        volatility = features.risk_metrics.get("annualized_volatility", 0.0)
        max_drawdown_3m = features.risk_metrics.get("max_drawdown_3m")
        max_drawdown_1y = features.risk_metrics.get("max_drawdown_1y")
        volatility_1m = features.risk_metrics.get("annualized_volatility_1m")
        volatility_3m = features.risk_metrics.get("annualized_volatility_3m")
        volatility_1y = features.risk_metrics.get("annualized_volatility_1y")
        available_window_count = features.data_quality_metrics.get("available_return_window_count", 0)

        raw_score = 82 + (max_drawdown * 90) - (volatility * 20)
        if max_drawdown_3m is not None:
            raw_score += max_drawdown_3m * 40
        if max_drawdown_1y is not None:
            raw_score += max_drawdown_1y * 30
        if volatility_1m is not None:
            raw_score -= volatility_1m * 10
        if volatility_3m is not None:
            raw_score -= volatility_3m * 12
        if volatility_1y is not None:
            raw_score -= volatility_1y * 14
        if available_window_count == 0:
            raw_score -= 5
        score = clamp(raw_score)
        stance = score_to_stance(score)

        system_prompt = (
            "You are a fund risk analyst. Explain the fund's main risk profile using only the provided risk metrics. "
            "Do not infer holdings, sectors, manager behavior, or market causes from outside knowledge."
        )
        user_prompt = (
            f"Fund: {features.fund_info.name} ({features.fund_info.code})\n"
            f"Max drawdown: {max_drawdown:.4f}\n"
            f"Annualized volatility: {volatility:.4f}\n"
            f"3M max drawdown: {max_drawdown_3m}\n"
            f"1Y max drawdown: {max_drawdown_1y}\n"
            f"1M annualized volatility: {volatility_1m}\n"
            f"3M annualized volatility: {volatility_3m}\n"
            f"1Y annualized volatility: {volatility_1y}\n"
            f"Data quality flags: {features.data_quality_flags}\n"
            f"Missing fields: {features.missing_fields}\n"
            "Please explain risk level, risk sources, and investor suitability."
        )
        fallback_narrative = (
            f"Deterministic risk analysis scored {score:.1f}/100 with a {stance} stance. "
            f"Annualized volatility is {volatility:.2%} and maximum drawdown is {max_drawdown:.2%}. "
            "The optional LLM explanation was unavailable; the score and structured evidence remain valid."
        )
        narrative, narrative_metadata = self.explain_or_fallback(
            system_prompt,
            user_prompt,
            fallback_narrative,
        )

        key_points = [
            f"Annualized volatility is {volatility:.2%}.",
            f"Max drawdown is {max_drawdown:.2%}.",
        ]
        if volatility_3m is not None:
            key_points.append(f"3-month annualized volatility is {volatility_3m:.2%}.")
        if volatility_1y is not None:
            key_points.append(f"1-year annualized volatility is {volatility_1y:.2%}.")
        if max_drawdown_1y is not None:
            key_points.append(f"1-year max drawdown is {max_drawdown_1y:.2%}.")

        risks = []
        if volatility > 0.35:
            risks.append("Volatility is high for a conservative investor.")
        if volatility_1m is not None and volatility_3m is not None and volatility_1m > volatility_3m:
            risks.append("Short-term volatility is running above the medium-term average.")
        if max_drawdown < -0.20:
            risks.append("Drawdown tolerance needs to be strong.")
        if max_drawdown_1y is not None and max_drawdown_1y < -0.20:
            risks.append("The 1-year drawdown profile still looks heavy for low-risk capital.")
        if available_window_count < 2:
            risks.append("Risk history is still too short for a fuller rolling-risk assessment.")

        recommendations = ["Size the position based on your drawdown tolerance."]
        if not risks:
            recommendations = ["Risk profile looks moderate under the current sample metrics."]
        elif available_window_count < 2:
            recommendations = ["Treat the current risk read as preliminary until a longer history is available."]

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
            metadata=narrative_metadata,
        )
