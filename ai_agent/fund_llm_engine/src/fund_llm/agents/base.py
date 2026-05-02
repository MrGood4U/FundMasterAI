from abc import ABC, abstractmethod
from typing import List

from fund_llm.contracts import AgentOutput, FundFeaturePack


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


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

    def safe_analyze(self, features: FundFeaturePack) -> AgentOutput:
        try:
            return self.analyze(features)
        except Exception as exc:
            return AgentOutput(
                agent_name=self.name,
                status="error",
                score=None,
                stance="mixed",
                key_points=[],
                risks=[f"{self.name} failed: {exc}"],
                recommendations=["Check the upstream payload or prompt formatting."],
                confidence=0.0,
                narrative=f"{self.name} failed: {exc}",
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

