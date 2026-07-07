"""Peer/market context agent (Phase B2 lightweight version).

证据来源是两个已结构化的后端工具结果：

- `individual_analysis`（get_fund_individual_analysis）：分周期的同类比较，
  `risk_return_ratio_vs_peers` / `risk_robustness_vs_peers` 为 0-100 百分位，
  表示优于百分之多少的同类基金；
- `profit_probability`（get_fund_profit_probability）：按持有期统计的
  历史盈利概率与平均收益。

两类数据都缺失时输出 skipped + insufficient_data，不让 LLM 编造
市场判断。资金流（CapitalFlowAgent）因上游无数据源，保持未接入。
"""

from typing import Any, Dict, List, Optional

from fund_llm.agents.base import BaseAgent, clamp, data_driven_confidence, score_to_stance
from fund_llm.contracts import AgentOutput, FundFeaturePack


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except ValueError:
        return None


def _peer_percentiles(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed = []
    for row in rows:
        percentile = _to_float(row.get("risk_return_ratio_vs_peers"))
        if percentile is None:
            continue
        parsed.append(
            {
                "period": str(row.get("period") or "").strip() or "unknown",
                "risk_return_percentile": percentile,
                "robustness_percentile": _to_float(row.get("risk_robustness_vs_peers")),
            }
        )
    return parsed


def _profit_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed = []
    for row in rows:
        probability = _to_float(row.get("profit_probability"))
        if probability is None:
            continue
        parsed.append(
            {
                "holding_period": str(row.get("holding_period") or "").strip() or "unknown",
                "profit_probability": probability,
                "average_return": _to_float(row.get("average_return")),
            }
        )
    return parsed


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


class MarketAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "MarketAgent"

    def analyze(self, features: FundFeaturePack) -> AgentOutput:
        peer_rows = _peer_percentiles(features.individual_analysis)
        profit_rows = _profit_rows(features.profit_probability)

        if not peer_rows and not profit_rows:
            return AgentOutput(
                agent_name=self.name,
                status="skipped",
                score=None,
                stance="insufficient_data",
                key_points=["No peer-comparison or holding-period probability data was provided."],
                risks=[
                    "Market/peer context was skipped because upstream peer and probability data is missing."
                ],
                recommendations=[
                    "Add peer-comparison or profit-probability data before drawing market-context conclusions."
                ],
                confidence=0.0,
                narrative=(
                    "Market context skipped: no peer-comparison or profit-probability evidence "
                    "was provided, so no market-level judgement is made."
                ),
            )

        peer_percentiles = [row["risk_return_percentile"] for row in peer_rows]
        mean_peer_percentile = _mean(peer_percentiles)
        probabilities = [row["profit_probability"] for row in profit_rows]
        mean_probability = _mean(probabilities)

        raw_score = 55.0
        if peer_rows:
            # 百分位 50 为中位数：高于中位加分，低于中位减分。
            raw_score += (mean_peer_percentile - 50.0) * 0.5
        if profit_rows:
            raw_score += (mean_probability - 50.0) * 0.3
        score = clamp(raw_score)
        stance = score_to_stance(score)

        system_prompt = (
            "You are a fund market-context analyst. Explain how this fund stands versus peer funds "
            "and how holding-period profit probabilities look, using only the provided rows. "
            "Percentile fields mean the fund outperforms that percentage of peer funds. "
            "Do not infer market trends, fund flows, or macro views from outside knowledge."
        )
        user_prompt = (
            f"Fund: {features.fund_info.name} ({features.fund_info.code})\n"
            f"Normalized fund type: {features.normalized_fund_type}\n"
            f"Peer comparison rows: {peer_rows}\n"
            f"Holding-period profit probability rows: {profit_rows}\n"
            f"Client risk profile: {features.extra_context.get('client_risk_profile', '')}\n"
            f"Data quality flags: {features.data_quality_flags}\n"
            "Please explain the fund's peer standing and holding-period win-rate profile."
        )
        narrative = self.llm_client.chat(system_prompt, user_prompt)

        key_points = []
        if peer_rows:
            latest = peer_rows[0]
            key_points.append(
                f"Risk-adjusted return outperforms {latest['risk_return_percentile']:.0f}% of peers "
                f"over {latest['period']}."
            )
            if len(peer_rows) > 1:
                key_points.append(
                    f"Average peer percentile across {len(peer_rows)} periods is {mean_peer_percentile:.0f}."
                )
        if profit_rows:
            longest = profit_rows[-1]
            key_points.append(
                f"Historical profit probability is {longest['profit_probability']:.0f}% when held for "
                f"{longest['holding_period']}."
            )

        risks = []
        if peer_rows and mean_peer_percentile < 40:
            risks.append("The fund lags most peers on risk-adjusted return across the reported periods.")
        low_probability_rows = [row for row in profit_rows if row["profit_probability"] < 50]
        if low_probability_rows:
            risks.append(
                "Short holding periods historically had below-50% profit probability; "
                "the holding horizon matters."
            )
        robustness_values = [
            row["robustness_percentile"] for row in peer_rows if row["robustness_percentile"] is not None
        ]
        if robustness_values and _mean(robustness_values) < 45:
            risks.append("Risk robustness versus peers is below average, so drawdown control lags the category.")

        recommendations = ["Use peer standing and holding-period win rates as market context, not as a standalone signal."]
        if profit_rows and mean_probability >= 60:
            recommendations = [
                "Historical win rates favor longer holding periods; align the holding horizon accordingly."
            ]
        elif peer_rows and mean_peer_percentile < 40:
            recommendations = ["Compare stronger peer-category alternatives before adding exposure."]

        return AgentOutput(
            agent_name=self.name,
            status="success",
            score=score,
            stance=stance,
            key_points=key_points,
            risks=risks,
            recommendations=recommendations,
            confidence=data_driven_confidence(
                features,
                required_flags=["has_individual_analysis", "has_profit_probability"],
            ),
            narrative=narrative,
        )
