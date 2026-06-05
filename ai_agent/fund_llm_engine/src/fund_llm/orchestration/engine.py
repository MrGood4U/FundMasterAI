from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List

from fund_llm.contracts import AnalysisTraceEvent, FinalAnalysisResult, FundAnalysisInput
from fund_llm.feature_builder import FeatureBuilder


AGENT_TRACE_COPY = {
    "PerformanceAgent": (
        "Evaluated performance",
        "Checked absolute returns, rolling return windows, drawdown, and any available benchmark-relative metrics.",
    ),
    "RiskAgent": (
        "Measured risk profile",
        "Checked volatility, maximum drawdown, and rolling risk windows before judging suitability.",
    ),
    "ExposureAgent": (
        "Checked portfolio exposure",
        "Reviewed concentration signals such as top holdings weight and industry exposure when available.",
    ),
    "SentimentAgent": (
        "Reviewed news and announcements",
        "Used recent news or announcement signals as a secondary cross-check rather than a primary return driver.",
    ),
    "SectorAgent": (
        "Checked sector context",
        "Assessed sector concentration only when sector exposure data was available for this fund type.",
    ),
}


def _rounded(value):
    return round(value, 4) if isinstance(value, float) else value


def _build_feature_trace(features) -> AnalysisTraceEvent:
    return AnalysisTraceEvent(
        category="feature",
        title="Calculated fund metrics",
        detail=(
            "Transformed backend data into return, volatility, drawdown, exposure, "
            "benchmark, and data-quality features before any final recommendation."
        ),
        status="success",
        evidence={
            "nav_points": features.data_quality_metrics.get("nav_point_count", 0),
            "return_1y": _rounded(features.return_metrics.get("return_1y")),
            "return_6m": _rounded(features.return_metrics.get("return_6m")),
            "max_drawdown": _rounded(features.risk_metrics.get("max_drawdown")),
            "annualized_volatility": _rounded(features.risk_metrics.get("annualized_volatility")),
            "missing_fields": list(features.missing_fields),
        },
        technical={
            "fund_family": features.fund_family,
            "normalized_fund_type": features.normalized_fund_type,
            "return_metric_count": len(features.return_metrics),
            "risk_metric_count": len(features.risk_metrics),
            "benchmark_metric_count": len(features.benchmark_metrics),
            "data_coverage": dict(features.data_coverage),
            "data_quality_flags": dict(features.data_quality_flags),
        },
    )


def _build_agent_trace(output) -> AnalysisTraceEvent:
    title, detail = AGENT_TRACE_COPY.get(
        output.agent_name,
        (output.agent_name, "Ran one specialist analysis module and recorded its evidence, status, and score."),
    )
    status = output.status
    if output.status == "skipped":
        status = "warning"

    return AnalysisTraceEvent(
        category="agent",
        title=title,
        detail=detail,
        status=status,
        evidence={
            "stance": output.stance,
            "score": _rounded(output.score),
            "confidence": _rounded(output.confidence),
            "key_points": list(output.key_points[:2]),
            "risks": list(output.risks[:2]),
        },
        technical={
            "agent_name": output.agent_name,
            "raw_status": output.status,
        },
    )


def _build_aggregation_trace(result: FinalAnalysisResult, worker_count: int) -> AnalysisTraceEvent:
    successful_count = len([output for output in result.agent_outputs if output.status == "success"])
    skipped_count = len([output for output in result.agent_outputs if output.status == "skipped"])
    error_count = len([output for output in result.agent_outputs if output.status == "error"])
    return AnalysisTraceEvent(
        category="aggregation",
        title="Combined specialist views",
        detail=(
            "Aggregated successful specialist scores, confidence, skipped modules, and missing data "
            "into one final rating and action plan."
        ),
        status="success" if not error_count else "warning",
        evidence={
            "overall_rating": result.overall_rating,
            "overall_score": result.overall_score,
            "successful_agents": successful_count,
            "skipped_agents": skipped_count,
            "error_agents": error_count,
        },
        technical={
            "execution_mode": "parallel" if worker_count > 1 else "serial",
            "agent_worker_count": worker_count,
        },
    )


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
        trace = [_build_feature_trace(features)]
        trace.extend(_build_agent_trace(output) for output in agent_outputs)
        trace.append(_build_aggregation_trace(result, worker_count))
        result.analysis_trace = trace
        result.metadata.update(
            {
                "agent_execution_mode": "parallel" if worker_count > 1 else "serial",
                "agent_worker_count": str(worker_count),
            }
        )
        return result
