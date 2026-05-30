from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List

from fund_llm.contracts import FinalAnalysisResult, FundAnalysisInput
from fund_llm.feature_builder import FeatureBuilder


@dataclass
class AnalysisEngine:
    feature_builder: FeatureBuilder
    agents: List
    chief_agent: object
    max_workers: int | None = None

    def _agent_worker_count(self) -> int:
        if not self.agents:
            return 0

        worker_count = self.max_workers or len(self.agents)
        return max(1, min(worker_count, len(self.agents)))

    def _run_agents(self, features):
        if not self.agents:
            return []

        worker_count = self._agent_worker_count()
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(agent.safe_analyze, features) for agent in self.agents]
            return [future.result() for future in futures]

    def run(self, payload: FundAnalysisInput) -> FinalAnalysisResult:
        features = self.feature_builder.build(payload)
        agent_outputs = self._run_agents(features)
        result = self.chief_agent.aggregate(features, agent_outputs)
        worker_count = self._agent_worker_count()
        result.metadata.update(
            {
                "agent_execution_mode": "parallel" if worker_count > 1 else "serial",
                "agent_worker_count": str(worker_count),
            }
        )
        return result
