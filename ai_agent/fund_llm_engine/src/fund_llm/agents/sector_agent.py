from fund_llm.agents.base import BaseAgent, clamp, score_to_stance
from fund_llm.contracts import AgentOutput, FundFeaturePack


class SectorAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "SectorAgent"

    def analyze(self, features: FundFeaturePack) -> AgentOutput:
        industry_exposure = features.industry_exposure_breakdown
        sector_analysis_applicable = features.data_quality_flags.get("sector_analysis_applicable", True)
        if not sector_analysis_applicable:
            if features.fund_family == "etf_feeder":
                return AgentOutput(
                    agent_name=self.name,
                    status="skipped",
                    score=None,
                    stance="not_applicable",
                    key_points=[
                        "ETF feeder direct sector rows do not represent the tracked index exposure."
                    ],
                    risks=[],
                    recommendations=[
                        "Use target-ETF or tracked-index sector data for a look-through sector assessment."
                    ],
                    confidence=0.0,
                    narrative=(
                        "Sector analysis skipped: direct sector rows in an ETF feeder are not representative "
                        "of the tracked exposure, and look-through analysis is not yet available."
                    ),
                )
            return AgentOutput(
                agent_name=self.name,
                status="skipped",
                score=None,
                stance="not_applicable",
                key_points=[
                    f"Equity sector analysis is not applicable to {features.normalized_fund_type}."
                ],
                risks=[],
                recommendations=[
                    "Use asset-class or bond-holding exposure data instead of equity industry buckets."
                ],
                confidence=0.0,
                narrative=(
                    "Sector analysis skipped: this fund type does not have meaningful equity industry "
                    "exposure under the current data model."
                ),
            )

        has_industry_exposure = features.data_quality_flags.get("has_industry_exposure", False)
        if not has_industry_exposure:
            return AgentOutput(
                agent_name=self.name,
                status="skipped",
                score=None,
                stance="insufficient_data",
                key_points=["No industry exposure breakdown was provided."],
                risks=["Sector analysis was skipped because industry exposure data is missing."],
                recommendations=["Add a fuller industry breakdown before making sector-level conclusions."],
                confidence=0.0,
                narrative="Sector analysis skipped: industry exposure data was not provided.",
            )

        client_risk_profile = features.extra_context.get("client_risk_profile", "")

        ranked_sectors = sorted(industry_exposure.items(), key=lambda item: item[1], reverse=True)
        sector_count = len(ranked_sectors)
        top_sector_name, top_sector_weight = ranked_sectors[0] if ranked_sectors else ("unknown", 0.0)
        second_sector_name, second_sector_weight = ranked_sectors[1] if len(ranked_sectors) > 1 else ("", 0.0)
        top_two_weight = top_sector_weight + second_sector_weight

        news_topic_hits = []
        for item in features.news_items:
            text = " ".join(part for part in [item.title, item.summary, item.topic] if part)
            for sector_name, _ in ranked_sectors[:3]:
                if sector_name and sector_name in text and sector_name not in news_topic_hits:
                    news_topic_hits.append(sector_name)

        raw_score = 68.0
        if has_industry_exposure:
            raw_score -= top_sector_weight * 22
            raw_score -= top_two_weight * 12
            raw_score += min(sector_count, 5) * 1.8
            if sector_count >= 4:
                raw_score += 2
            if top_sector_weight > 0.40:
                raw_score -= 4
            if top_two_weight > 0.60:
                raw_score -= 3
            if news_topic_hits:
                raw_score += 1.5
        else:
            raw_score -= 10

        if client_risk_profile in {"balanced", "conservative"} and top_sector_weight > 0.35:
            raw_score -= 4

        score = clamp(raw_score)
        stance = score_to_stance(score)

        top_sectors_text = ", ".join(f"{name}:{weight:.1%}" for name, weight in ranked_sectors[:3]) or "N/A"
        system_prompt = (
            "You are a sector allocation analyst. Explain whether the fund's industry positioning looks diversified "
            "or concentrated, and what that means for sector-style exposure. Use only the provided sector data. "
            "Do not infer sectors or holdings from the fund name, manager, or outside knowledge."
        )
        user_prompt = (
            f"Fund: {features.fund_info.name} ({features.fund_info.code})\n"
            f"Category: {features.fund_info.category}\n"
            f"Industry exposure breakdown: {industry_exposure}\n"
            f"Top sectors: {top_sectors_text}\n"
            f"Sector count: {sector_count}\n"
            f"Top sector weight: {top_sector_weight:.4f}\n"
            f"Top two sector weight: {top_two_weight:.4f}\n"
            f"Fund tags: {features.fund_tags}\n"
            f"News topics touching top sectors: {news_topic_hits}\n"
            f"Client risk profile: {client_risk_profile}\n"
            f"Data quality flags: {features.data_quality_flags}\n"
            f"Missing fields: {features.missing_fields}\n"
            "Please explain the sector positioning in concise investment language."
        )
        fallback_narrative = (
            f"Deterministic sector analysis scored {score:.1f}/100 with a {stance} stance. "
            f"The largest disclosed sector is {top_sector_name} at {top_sector_weight:.2%}, "
            f"across {sector_count} sector bucket(s). The optional LLM explanation was unavailable; "
            "the score and structured evidence remain valid."
        )
        narrative, narrative_metadata = self.explain_or_fallback(
            system_prompt,
            user_prompt,
            fallback_narrative,
        )

        key_points = []
        if has_industry_exposure:
            key_points.append(f"Top sector is {top_sector_name} at {top_sector_weight:.2%}.")
            if second_sector_name:
                key_points.append(f"Top two sectors together account for {top_two_weight:.2%}.")
            key_points.append(f"Sector breadth covers {sector_count} disclosed sector bucket(s).")
            if news_topic_hits:
                key_points.append(f"Recent news flow overlaps with {', '.join(news_topic_hits)} sector themes.")
        else:
            key_points.append("No industry exposure breakdown was provided.")

        risks = []
        if not has_industry_exposure:
            risks.append("Sector view is incomplete because industry exposure data is missing.")
        else:
            if top_sector_weight > 0.40:
                risks.append("Single-sector exposure is relatively concentrated.")
            if top_two_weight > 0.60:
                risks.append("The fund relies heavily on its top two sector bets.")
            if client_risk_profile in {"balanced", "conservative"} and top_sector_weight > 0.35:
                risks.append(f"Current sector tilt may feel aggressive for a {client_risk_profile} profile.")

        recommendations = ["Use sector allocation as a cross-check, not a replacement for fund-level analysis."]
        if not has_industry_exposure:
            recommendations = ["Add a fuller industry breakdown before making sector-level conclusions."]
        elif not risks:
            recommendations = ["Sector positioning looks reasonably balanced for diversified allocation."]
        elif top_sector_weight > 0.40:
            recommendations = ["Watch whether the largest sector bet still matches your market view before sizing up."]

        confidence = 0.56
        if has_industry_exposure:
            confidence += 0.14
        if sector_count >= 3:
            confidence += 0.06
        if news_topic_hits:
            confidence += 0.04
        confidence = min(confidence, 0.84)

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
            metadata=narrative_metadata,
        )
