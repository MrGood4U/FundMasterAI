from fund_llm.agents.base import BaseAgent, clamp, score_to_stance
from fund_llm.contracts import AgentOutput, FundFeaturePack


class ExposureAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "ExposureAgent"

    def analyze(self, features: FundFeaturePack) -> AgentOutput:
        industry_concentration = features.exposure_metrics.get("industry_concentration", 0.0)
        top_holdings_weight = features.exposure_metrics.get("top_holdings_weight", 0.0)
        has_industry_exposure = features.data_quality_flags.get("has_industry_exposure", False)
        has_top_holdings = features.data_quality_flags.get("has_top_holdings_weight", False)
        fund_tags = features.fund_tags[:3]
        manager_tenure = features.operational_metrics.manager_tenure_years
        fund_size = features.operational_metrics.fund_size_billion
        client_risk_profile = features.extra_context.get("client_risk_profile", "")

        raw_score = 72 - (industry_concentration * 55) - (top_holdings_weight * 22)
        if manager_tenure is not None:
            raw_score += min(manager_tenure, 8.0) * 1.1
        if fund_size is not None:
            if 2 <= fund_size <= 80:
                raw_score += 2
            elif fund_size < 1:
                raw_score -= 2
        if "core_holding" in fund_tags and industry_concentration <= 0.35 and top_holdings_weight <= 0.50:
            raw_score += 2
        if not has_industry_exposure:
            raw_score -= 8
        if not has_top_holdings:
            raw_score -= 5
        if client_risk_profile in {"balanced", "conservative"} and (
            industry_concentration > 0.35 or top_holdings_weight > 0.55
        ):
            raw_score -= 4
        score = clamp(raw_score)
        stance = score_to_stance(score)

        system_prompt = "You are a fund exposure analyst. Explain the portfolio concentration and exposure profile."
        user_prompt = (
            f"Fund: {features.fund_info.name} ({features.fund_info.code})\n"
            f"Category: {features.fund_info.category}\n"
            f"Industry concentration: {industry_concentration:.4f}\n"
            f"Top holdings weight: {top_holdings_weight:.4f}\n"
            f"Fund tags: {fund_tags}\n"
            f"Fund size (billion): {fund_size}\n"
            f"Manager tenure (years): {manager_tenure}\n"
            f"Client risk profile: {client_risk_profile}\n"
            f"Data quality flags: {features.data_quality_flags}\n"
            f"Missing fields: {features.missing_fields}\n"
            f"News summary: {features.news_summary}\n"
            "Please explain whether the exposure looks concentrated or diversified."
        )
        narrative = self.llm_client.chat(system_prompt, user_prompt)

        key_points = [
            f"Industry concentration is {industry_concentration:.2%}.",
            f"Top holdings weight is {top_holdings_weight:.2%}.",
        ]
        if fund_tags:
            key_points.append(f"Fund role/style tags include {', '.join(fund_tags)}.")
        if manager_tenure is not None:
            key_points.append(f"Manager tenure is {manager_tenure:.1f} years.")
        if fund_size is not None:
            key_points.append(f"Fund size is about {fund_size:.1f} billion.")

        risks = []
        if industry_concentration > 0.35:
            risks.append("Industry exposure is concentrated.")
        if top_holdings_weight > 0.55:
            risks.append("Top holdings weight is relatively high.")
        if not has_industry_exposure or not has_top_holdings:
            risks.append("Exposure read is incomplete because portfolio breakdown fields are still missing.")
        if client_risk_profile in {"balanced", "conservative"} and (
            industry_concentration > 0.35 or top_holdings_weight > 0.55
        ):
            risks.append(f"Current concentration may feel aggressive for a {client_risk_profile} risk profile.")

        recommendations = ["Use this fund alongside positions from other sectors or styles."]
        if not has_industry_exposure or not has_top_holdings:
            recommendations = ["Confirm the full holdings and industry breakdown before sizing the position."]
        elif risks and client_risk_profile in {"balanced", "conservative"}:
            recommendations = [f"Keep any allocation sized for a {client_risk_profile} risk profile and diversify around it."]
        elif not risks and "core_holding" in fund_tags:
            recommendations = ["Exposure profile looks consistent with a core allocation role."]
        elif not risks:
            recommendations = ["Exposure profile looks acceptable for diversified allocation."]

        confidence = 0.66
        if has_industry_exposure and has_top_holdings:
            confidence += 0.10
        if fund_tags or manager_tenure is not None or fund_size is not None:
            confidence += 0.04

        return AgentOutput(
            agent_name=self.name,
            status="success",
            score=score,
            stance=stance,
            key_points=key_points,
            risks=risks,
            recommendations=recommendations,
            confidence=confidence,
            narrative=narrative,
        )
