"""Portfolio-level chief aggregation (Phase A1).

先用确定性规则算组合评分/评级/要点，再让 LLM 只负责把已算好的证据
写成用户可读的英文总评。LLM 失败或输出不完整时回退到确定性摘要，
与单基金 `ChiefAgent` 的防幻觉策略一致。
"""

from typing import Dict, List

from fund_llm.agents.base import clamp
from fund_llm.agents.chief_agent import _score_to_rating, _summary_looks_incomplete
from fund_llm.contracts import PortfolioConstituentMetrics

# 与 chief_agent 相同的年化指标可靠性阈值口径。
QUANT_RELIABLE_MIN_POINTS = 252
QUANT_LIMITED_MIN_POINTS = 120


def _reliability_label(sample_size: int) -> str:
    if sample_size >= QUANT_RELIABLE_MIN_POINTS:
        return "high"
    if sample_size >= QUANT_LIMITED_MIN_POINTS:
        return "medium"
    return "low"


def compute_portfolio_score(quant_metrics: Dict[str, float]) -> float:
    """Deterministic portfolio score on the fund-level 0-100 scale.

    与单基金各 agent 的打分习惯一致：从中性基线出发，用收益、回撤、
    风险调整收益和分散化效应做加减，最后 clamp 到 0-100。
    """
    total_return = quant_metrics.get("total_return", 0.0)
    max_drawdown = quant_metrics.get("max_drawdown", 0.0)
    sharpe_ratio = quant_metrics.get("sharpe_ratio", 0.0)
    diversification_benefit = quant_metrics.get("diversification_benefit", 0.0)

    raw_score = 58 + (total_return * 150) + (max_drawdown * 40)
    raw_score += clamp(sharpe_ratio, -2.0, 3.0) * 6
    # 分散化收益按年化波动率之差计价：每降低 1 个百分点波动 +0.8 分，封顶 8 分。
    raw_score += clamp(diversification_benefit * 80, 0.0, 8.0)
    return round(clamp(raw_score), 2)


class PortfolioChiefAgent:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def aggregate(
        self,
        quant_metrics: Dict[str, float],
        constituents: List[PortfolioConstituentMetrics],
        client_risk_profile: str = "balanced",
        weights_rescaled: bool = False,
        lookthrough: Dict[str, dict] | None = None,
    ) -> Dict[str, object]:
        overall_score = compute_portfolio_score(quant_metrics)
        overall_rating = _score_to_rating(overall_score)
        sample_size = int(quant_metrics.get("sample_size", 0))
        reliability = _reliability_label(sample_size)

        total_return = quant_metrics.get("total_return", 0.0)
        annualized_volatility = quant_metrics.get("annualized_volatility", 0.0)
        max_drawdown = quant_metrics.get("max_drawdown", 0.0)
        sharpe_ratio = quant_metrics.get("sharpe_ratio", 0.0)
        weighted_average_volatility = quant_metrics.get("weighted_average_volatility", 0.0)
        diversification_benefit = quant_metrics.get("diversification_benefit", 0.0)

        best = max(constituents, key=lambda item: item.total_return)
        worst = min(constituents, key=lambda item: item.total_return)

        key_thesis = [
            f"The composed portfolio returned {total_return:.2%} over the shared {sample_size}-day NAV window.",
            f"Portfolio annualized volatility is {annualized_volatility:.2%} with a max drawdown of {max_drawdown:.2%}.",
        ]
        if diversification_benefit > 0.0005:
            key_thesis.append(
                f"Diversification reduced volatility by {diversification_benefit:.2%} versus the "
                f"weighted average of constituent volatilities ({weighted_average_volatility:.2%})."
            )
        if len(constituents) > 1:
            key_thesis.append(
                f"The strongest constituent is {best.name} ({best.code}) at {best.total_return:.2%}, "
                f"the weakest is {worst.name} ({worst.code}) at {worst.total_return:.2%}."
            )

        # 持仓穿透证据（A2）：只在数据可用时陈述，缺数据不编造。
        lookthrough = lookthrough or {}
        holdings_view = lookthrough.get("holdings") or {}
        industry_view = lookthrough.get("industry") or {}
        allocation_view = lookthrough.get("asset_allocation") or {}
        lookthrough_risks: List[str] = []

        if holdings_view.get("status") in {"available", "partial"}:
            top_rows = holdings_view.get("top_holdings") or []
            if top_rows:
                top_row = top_rows[0]
                key_thesis.append(
                    f"Look-through top holding is {top_row['stock_name'] or top_row['stock_code']} at "
                    f"{top_row['portfolio_weight']:.2%} of the portfolio "
                    f"(disclosed holdings cover {holdings_view.get('disclosed_weight_total', 0.0):.2%})."
                )
            overlaps = holdings_view.get("overlapping_holdings") or []
            if overlaps:
                overlap_row = overlaps[0]
                lookthrough_risks.append(
                    f"{overlap_row['stock_name'] or overlap_row['stock_code']} is held by "
                    f"{len(overlap_row['held_by'])} constituent funds at a combined "
                    f"{overlap_row['portfolio_weight']:.2%}, so the funds overlap more than the weights suggest."
                )
        if industry_view.get("status") in {"available", "partial"}:
            top_sector_weight = float(industry_view.get("top_sector_weight") or 0.0)
            top_sectors = industry_view.get("top_sectors") or []
            if top_sectors:
                key_thesis.append(
                    f"Look-through top sector is {top_sectors[0]['sector']} at "
                    f"{top_sectors[0]['portfolio_weight']:.2%} of the portfolio."
                )
            if top_sector_weight > 0.30:
                lookthrough_risks.append(
                    f"Portfolio-level exposure to {top_sectors[0]['sector']} reaches "
                    f"{top_sector_weight:.2%}, which concentrates sector risk."
                )
        if allocation_view.get("status") in {"available", "partial"}:
            buckets = allocation_view.get("buckets") or {}
            key_thesis.append(
                "Look-through asset mix is "
                f"stock {buckets.get('stock', 0.0):.2%}, bond {buckets.get('bond', 0.0):.2%}, "
                f"cash {buckets.get('cash', 0.0):.2%}."
            )

        main_risks = list(lookthrough_risks)
        if max_drawdown < -0.15:
            main_risks.append("Portfolio drawdown history is meaningful and needs drawdown tolerance.")
        if annualized_volatility > 0.25:
            main_risks.append("Portfolio volatility is elevated for conservative capital.")
        top_weight = max(constituents, key=lambda item: item.weight)
        if top_weight.weight > 0.6:
            main_risks.append(
                f"Allocation is concentrated: {top_weight.name} ({top_weight.code}) holds "
                f"{top_weight.weight:.0%} of the portfolio."
            )
        if reliability != "high":
            main_risks.append(
                f"The shared NAV window has only {sample_size} points, so annualized metrics are "
                f"{reliability}-reliability estimates."
            )
        if not main_risks:
            main_risks.append("No outsized risk flag was triggered under the current shared-window metrics.")

        action_plan = [f"Match the allocation to a {client_risk_profile} risk profile."]
        if weights_rescaled:
            action_plan.append("Input weights did not sum to 1 and were proportionally rescaled before analysis.")
        if diversification_benefit <= 0.0005 and len(constituents) > 1:
            action_plan.append(
                "Constituents move closely together; consider adding less-correlated assets for real diversification."
            )
        if reliability != "high":
            action_plan.append("Re-check the portfolio once a longer shared NAV history is available.")

        score_explanation = (
            f"The {overall_rating.upper()} rating reflects a deterministic portfolio score of "
            f"{overall_score:.1f}/100 computed from the composed NAV series: total return "
            f"{total_return:.2%}, max drawdown {max_drawdown:.2%}, Sharpe ratio {sharpe_ratio:.2f}, "
            f"and a diversification benefit of {diversification_benefit:.2%} in annualized volatility. "
            f"Metrics use {sample_size} shared NAV points ({reliability} reliability)."
        )

        constituent_lines = "\n".join(
            f"- {item.name} ({item.code}) weight={item.weight:.2%} type={item.normalized_fund_type} "
            f"return={item.total_return:.2%} vol={item.annualized_volatility:.2%} "
            f"max_drawdown={item.max_drawdown:.2%} sharpe={item.sharpe_ratio:.2f}"
            for item in constituents
        )
        lookthrough_block = "Not available."
        lookthrough_parts = []
        if holdings_view.get("status") in {"available", "partial"}:
            lookthrough_parts.append(
                f"Top combined holdings: {holdings_view.get('top_holdings', [])[:5]} | "
                f"overlapping holdings: {holdings_view.get('overlapping_holdings', [])[:3]} | "
                f"disclosed weight total: {holdings_view.get('disclosed_weight_total')}"
            )
        if industry_view.get("status") in {"available", "partial"}:
            lookthrough_parts.append(f"Top sectors: {industry_view.get('top_sectors', [])[:5]}")
        if allocation_view.get("status") in {"available", "partial"}:
            lookthrough_parts.append(f"Asset buckets: {allocation_view.get('buckets', {})}")
        if lookthrough_parts:
            lookthrough_block = "\n".join(lookthrough_parts)

        system_prompt = (
            "You are the chief portfolio advisor. Summarize the portfolio-level findings into one final view. "
            "Respond in English only: even though fund names may be Chinese, the summary itself must be "
            "written in clear user-facing English. "
            "Use only the supplied portfolio metrics, constituent table, "
            "and holdings look-through evidence. "
            "Do not use outside knowledge about the funds, managers, holdings, or market narrative. "
            "Explain the diversification effect using the provided volatility comparison. "
            "If look-through evidence shows overlapping holdings or sector concentration, mention it. "
            "Do not state an overall score, signal, rating, or BUY/HOLD/WATCH/AVOID label; "
            "the consumer presents this output as narrative analysis only. "
            "Keep the final summary under 160 words and end with a complete sentence."
        )
        user_prompt = (
            f"Portfolio constituents:\n{constituent_lines}\n\n"
            f"Portfolio metrics: {quant_metrics}\n"
            f"Holdings look-through (quarterly top-10 disclosure basis):\n{lookthrough_block}\n"
            f"Sample size (shared NAV points): {sample_size} ({reliability} reliability)\n"
            f"Client risk profile: {client_risk_profile}\n"
            f"Key thesis candidates: {key_thesis}\n"
            f"Risk candidates: {main_risks}\n"
            f"Action plan candidates: {action_plan}\n\n"
            "Please write a concise final summary in two short paragraphs."
        )

        summary_source = "llm"
        try:
            summary = self.llm_client.chat(system_prompt, user_prompt, max_tokens=1000)
        except Exception:
            summary = ""
            summary_source = "deterministic_fallback"

        if (
            not getattr(self.llm_client, "is_mock", False)
            and _summary_looks_incomplete(summary)
        ):
            summary = ""
            summary_source = "deterministic_fallback"

        if not summary:
            summary = (
                f"The portfolio analysis uses {sample_size} shared NAV observations across "
                f"{len(constituents)} constituent fund(s). Total return is {total_return:.2%} with "
                f"{annualized_volatility:.2%} annualized volatility and a {max_drawdown:.2%} max drawdown. "
                f"Diversification lowered volatility by {diversification_benefit:.2%} versus the weighted "
                f"average of the constituents. Review the per-fund metrics before adjusting the allocation."
            )

        return {
            "overall_score": overall_score,
            "overall_rating": overall_rating,
            "key_thesis": key_thesis,
            "main_risks": main_risks,
            "action_plan": action_plan,
            "score_explanation": score_explanation,
            "summary": summary,
            "summary_source": summary_source,
            "quant_metrics_reliability": reliability,
        }
