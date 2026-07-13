from typing import Any, Dict, List

from fund_llm.agents.base import BaseAgent, clamp, score_to_stance
from fund_llm.contracts import AgentOutput, FundFeaturePack


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _holding_name(row: Dict[str, Any]) -> str:
    return str(row.get("bond_name") or row.get("name") or row.get("债券名称") or "").strip()


def _top_bond_names(holdings: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    names = [_holding_name(row) for row in holdings]
    return [name for name in names if name][:limit]


def _policy_bank_holding_count(holdings: List[Dict[str, Any]]) -> int:
    keywords = ("国开", "政策", "policy bank", "development bank")
    count = 0
    for row in holdings:
        name = _holding_name(row).lower()
        if any(keyword in name for keyword in keywords):
            count += 1
    return count


class BondExposureAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "BondExposureAgent"

    def analyze(self, features: FundFeaturePack) -> AgentOutput:
        bond_exposure_applicable = features.data_quality_flags.get("bond_exposure_applicable", False)
        if not bond_exposure_applicable:
            if features.fund_family == "etf_feeder":
                return AgentOutput(
                    agent_name=self.name,
                    status="skipped",
                    score=None,
                    stance="not_applicable",
                    key_points=[
                        "ETF feeder bond exposure is not assessed separately from the target ETF."
                    ],
                    risks=[],
                    recommendations=[
                        "Use target-ETF or tracked-index holdings for a look-through asset assessment."
                    ],
                    confidence=0.0,
                    narrative=(
                        "Bond exposure analysis skipped: an ETF feeder should be assessed through its target "
                        "ETF rather than residual direct holdings."
                    ),
                )
            return AgentOutput(
                agent_name=self.name,
                status="skipped",
                score=None,
                stance="not_applicable",
                key_points=[
                    f"Bond exposure analysis is not applicable to {features.normalized_fund_type}."
                ],
                risks=[],
                recommendations=[
                    "Use equity exposure and sector agents for non-bond fund types."
                ],
                confidence=0.0,
                narrative="Bond exposure analysis skipped: this fund type is not bond-like.",
            )

        has_bond_holdings = features.data_quality_flags.get("has_bond_holdings", False)
        has_asset_allocation = features.data_quality_flags.get("has_asset_allocation", False)
        if not has_bond_holdings and not has_asset_allocation:
            return AgentOutput(
                agent_name=self.name,
                status="skipped",
                score=None,
                stance="insufficient_data",
                key_points=["No bond holdings or asset-allocation data was provided."],
                risks=[
                    "Bond exposure analysis was skipped because both bond holdings and asset allocation are missing."
                ],
                recommendations=[
                    "Add bond holding detail or asset-allocation data before drawing fixed-income exposure conclusions."
                ],
                confidence=0.0,
                narrative="Bond exposure analysis skipped: no bond-specific exposure data was provided.",
            )

        invalid_sources = []
        if has_bond_holdings and not features.data_quality_flags.get("bond_holdings_valid", False):
            invalid_sources.append("bond holding weights")
        if has_asset_allocation and not features.data_quality_flags.get("asset_allocation_valid", False):
            invalid_sources.append("asset-allocation weights")
        if invalid_sources:
            invalid_text = " and ".join(invalid_sources)
            return AgentOutput(
                agent_name=self.name,
                status="error",
                score=None,
                stance="mixed",
                key_points=[f"Invalid {invalid_text} were rejected before scoring."],
                risks=[
                    "Bond exposure data failed finite, non-negative, or gross-exposure plausibility checks."
                ],
                recommendations=[
                    "Correct the percentage units or source records before using bond-exposure evidence."
                ],
                confidence=0.0,
                narrative=(
                    "Bond exposure analysis could not be scored because its percentage inputs "
                    "failed data-quality validation."
                ),
                metadata={"failure_stage": "bond_exposure_data_validation"},
            )

        metrics = features.bond_exposure_metrics
        holding_count = int(metrics.get("bond_holding_count", 0))
        allocation_count = int(metrics.get("asset_allocation_count", 0))
        top_holding_weight = metrics.get("bond_top_holding_weight", 0.0)
        top_three_weight = metrics.get("bond_top_three_weight", 0.0)
        total_disclosed_weight = metrics.get("bond_total_disclosed_weight", 0.0)
        asset_bond_weight = metrics.get("asset_bond_weight", 0.0)
        asset_cash_weight = metrics.get("asset_cash_weight", 0.0)
        asset_stock_weight = metrics.get("asset_stock_weight", 0.0)
        asset_other_weight = metrics.get("asset_other_weight", 0.0)
        client_risk_profile = features.extra_context.get("client_risk_profile", "")
        top_bond_names = _top_bond_names(features.bond_holdings)
        policy_bank_count = _policy_bank_holding_count(features.bond_holdings)

        raw_score = 68.0
        if has_asset_allocation:
            if asset_bond_weight >= 0.75:
                raw_score += 4
            elif asset_bond_weight and asset_bond_weight < 0.60:
                raw_score -= 5
            if asset_cash_weight >= 0.08:
                raw_score += 1
            if asset_stock_weight > 0.05:
                raw_score -= 8
        else:
            raw_score -= 5

        if has_bond_holdings:
            if top_holding_weight > 0.25:
                raw_score -= 4
            if top_three_weight > 0.65:
                raw_score -= 6
            elif top_three_weight > 0.50:
                raw_score -= 3
            if holding_count >= 5:
                raw_score += 2
            if policy_bank_count and policy_bank_count == holding_count:
                raw_score += 3
            elif policy_bank_count:
                raw_score += 1
        else:
            raw_score -= 6

        if client_risk_profile in {"balanced", "conservative", "income_oriented"}:
            if top_three_weight > 0.65:
                raw_score -= 2
            if asset_stock_weight > 0.03:
                raw_score -= 3

        score = clamp(raw_score)
        stance = score_to_stance(score)

        system_prompt = (
            "You are a fixed-income fund exposure analyst. Explain bond and asset-class exposure using only "
            "the provided holdings, asset allocation, data coverage, and metrics. Do not infer duration, "
            "issuer credit quality, ratings, or yield curve positioning unless those fields are supplied."
        )
        user_prompt = (
            f"Fund: {features.fund_info.name} ({features.fund_info.code})\n"
            f"Category: {features.fund_info.category}\n"
            f"Normalized fund type: {features.normalized_fund_type}\n"
            f"Bond exposure metrics: {metrics}\n"
            f"Asset allocation: {features.asset_allocation_breakdown}\n"
            f"Top bond holdings: {features.bond_holdings[:5]}\n"
            f"Top bond names: {top_bond_names}\n"
            f"Client risk profile: {client_risk_profile}\n"
            f"Data quality flags: {features.data_quality_flags}\n"
            f"Data coverage: {features.data_coverage}\n"
            f"Missing fields: {features.missing_fields}\n"
            "Please explain whether the fixed-income exposure is diversified, concentrated, or incomplete."
        )
        fallback_evidence = []
        if has_bond_holdings:
            fallback_evidence.append(f"{holding_count} disclosed bond holding(s)")
        if has_asset_allocation:
            fallback_evidence.append(f"{allocation_count} asset-allocation bucket(s)")
        fallback_narrative = (
            f"Deterministic bond-exposure analysis scored {score:.1f}/100 with a {stance} stance "
            f"using {' and '.join(fallback_evidence)}. The optional LLM explanation was unavailable; "
            "the score and structured evidence remain valid."
        )
        narrative, narrative_metadata = self.explain_or_fallback(
            system_prompt,
            user_prompt,
            fallback_narrative,
        )

        key_points = []
        if has_bond_holdings:
            key_points.append(f"Bond holdings are available for {holding_count} disclosed position(s).")
            key_points.append(f"Top bond holding weight is {_pct(top_holding_weight)}.")
            if holding_count >= 2:
                key_points.append(f"Top three bond holdings are {_pct(top_three_weight)} of NAV.")
            if total_disclosed_weight:
                key_points.append(f"Disclosed bond holdings sum to {_pct(total_disclosed_weight)} of NAV.")
            if top_bond_names:
                key_points.append(f"Top disclosed bonds include {', '.join(top_bond_names)}.")
        if has_asset_allocation:
            key_points.append(
                "Asset allocation shows "
                f"bond {_pct(asset_bond_weight)}, cash {_pct(asset_cash_weight)}, "
                f"stock {_pct(asset_stock_weight)}, other {_pct(asset_other_weight)}."
            )

        risks = []
        if not has_bond_holdings:
            risks.append("Bond holding details are missing, so issuer-level concentration cannot be checked.")
        if not has_asset_allocation:
            risks.append("Asset allocation is missing, so bond/cash/other exposure cannot be fully verified.")
        if top_holding_weight > 0.25:
            risks.append("The largest disclosed bond position is relatively concentrated.")
        if top_three_weight > 0.65:
            risks.append("Top bond holdings account for a high share of NAV.")
        if asset_stock_weight > 0.05:
            risks.append("Stock allocation is visible inside a bond-like fund and should be checked against mandate.")
        risks.append(
            "Duration and credit-rating fields were not provided, so rate and credit risk remain partially observable."
        )

        recommendations = ["Use bond exposure as a fixed-income-specific cross-check alongside performance and risk."]
        if not has_bond_holdings or not has_asset_allocation:
            recommendations = [
                "Collect the missing bond holding or asset-allocation data before assigning high conviction."
            ]
        elif top_three_weight > 0.65:
            recommendations = [
                "Check whether issuer, maturity, and duration concentration fit the intended fixed-income role."
            ]
        elif asset_bond_weight >= 0.75 and asset_stock_weight <= 0.03:
            recommendations = [
                "Bond allocation looks consistent with a fixed-income role; still confirm duration and credit quality."
            ]

        confidence = 0.46
        if has_bond_holdings:
            confidence += 0.17
        if has_asset_allocation:
            confidence += 0.15
        if holding_count >= 5:
            confidence += 0.05
        if allocation_count >= 3:
            confidence += 0.04
        confidence = min(confidence, 0.86)

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
