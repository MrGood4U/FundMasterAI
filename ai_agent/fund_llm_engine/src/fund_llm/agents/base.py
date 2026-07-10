from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from fund_llm.contracts import AgentOutput, FundFeaturePack


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


# 统一的数据驱动置信度口径（implementation_plan Phase C）。
# 置信度只反映“输入数据质量”，不反映观点强弱，因此约束在 0.4-0.9：
# 再缺数据也不会低于 0.4（agent 仍在已有证据上工作），再充分也不超过 0.9（保留模型不确定性）。
CONFIDENCE_FLOOR = 0.4
CONFIDENCE_CEILING = 0.9

# 约一个交易年的净值点数；达到后年化类指标的样本贡献封顶。
FULL_NAV_SAMPLE_POINTS = 252


def data_driven_confidence(
    features: FundFeaturePack,
    required_flags: Optional[List[str]] = None,
) -> float:
    """Compute agent confidence from input data quality signals.

    Signals（与 implementation_plan Phase C 对齐）:
    - NAV 点数：样本越长，年化指标越可靠，最高 +0.20；
    - 可用滚动回报窗口数（1m/3m/6m/1y）：每个 +0.04，最高 +0.16；
    - 是否有 benchmark：可做相对比较，+0.06；
    - 该 agent 所需数据齐全度（data_quality_flags 中的布尔项）：按满足比例最高 +0.08。
    """
    nav_points = features.data_quality_metrics.get("nav_point_count", 0)
    window_count = features.data_quality_metrics.get("available_return_window_count", 0)
    has_benchmark = features.data_quality_flags.get("has_benchmark", False)

    confidence = CONFIDENCE_FLOOR
    confidence += min(nav_points / FULL_NAV_SAMPLE_POINTS, 1.0) * 0.20
    confidence += min(window_count, 4) * 0.04
    if has_benchmark:
        confidence += 0.06
    if required_flags:
        satisfied = sum(
            1 for flag in required_flags if features.data_quality_flags.get(flag, False)
        )
        confidence += (satisfied / len(required_flags)) * 0.08
    else:
        # 该 agent 除 NAV 序列外没有额外必需字段，视为字段齐全。
        confidence += 0.08

    return round(clamp(confidence, CONFIDENCE_FLOOR, CONFIDENCE_CEILING), 2)


class BaseAgent(ABC):
    def __init__(self, llm_client):
        self.llm_client = llm_client

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def analyze(self, features: FundFeaturePack) -> AgentOutput:
        ...

    def explain_or_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_narrative: str,
    ) -> Tuple[str, Dict[str, str]]:
        """Generate the optional LLM explanation without risking the deterministic result.

        Specialist scores, stances, evidence, and confidence are computed before this
        helper is called. A provider failure therefore degrades only the narrative;
        it must not turn a completed deterministic analysis into an agent error.
        """
        try:
            narrative = self.llm_client.chat(system_prompt, user_prompt)
        except Exception:
            narrative = ""

        if isinstance(narrative, str) and narrative.strip():
            return narrative.strip(), {"narrative_source": "llm"}

        fallback = (fallback_narrative or "").strip()
        if not fallback:
            fallback = (
                f"{self.name} completed its deterministic analysis, but the optional "
                "LLM explanation was unavailable."
            )
        return fallback, {"narrative_source": "deterministic_fallback"}

    def safe_analyze(self, features: FundFeaturePack) -> AgentOutput:
        try:
            return self.analyze(features)
        except Exception:
            return AgentOutput(
                agent_name=self.name,
                status="error",
                score=None,
                stance="mixed",
                key_points=[],
                risks=[f"{self.name} could not complete its deterministic analysis."],
                recommendations=["Review the server logs and retry the analysis."],
                confidence=0.0,
                narrative=f"{self.name} could not complete its deterministic analysis.",
                metadata={"failure_stage": "deterministic_analysis"},
            )


def score_to_stance(score: float) -> str:
    if score >= 70:
        return "positive"
    if score <= 40:
        return "negative"
    return "neutral"


def merge_lists(items: List[List[str]], limit: int = 3) -> List[str]:
    merged = []
    for group in items:
        for item in group:
            if item not in merged:
                merged.append(item)
            if len(merged) >= limit:
                return merged
    return merged
