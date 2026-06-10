from fund_llm.agents import (
    BondExposureAgent,
    ChiefAgent,
    ExposureAgent,
    PerformanceAgent,
    RiskAgent,
    SectorAgent,
    SentimentAgent,
)
from fund_llm.contracts import FinalAnalysisResult, FundAnalysisInput
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.llm_client import LLMClient
from fund_llm.orchestration.engine import AnalysisEngine


def build_real_engine(
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    timeout_seconds: int = None,
    max_parallel_agents: int = None,
) -> AnalysisEngine:
    llm_client = LLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
    )
    return AnalysisEngine(
        feature_builder=FeatureBuilder(),
        agents=[
            PerformanceAgent(llm_client),
            ExposureAgent(llm_client),
            BondExposureAgent(llm_client),
            RiskAgent(llm_client),
            SentimentAgent(llm_client),
            SectorAgent(llm_client),
        ],
        chief_agent=ChiefAgent(llm_client),
        max_workers=max_parallel_agents,
    )


def run_real_analysis_for_input(
    payload: FundAnalysisInput,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    timeout_seconds: int = None,
    max_parallel_agents: int = None,
) -> FinalAnalysisResult:
    engine = build_real_engine(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        max_parallel_agents=max_parallel_agents,
    )
    result = engine.run(payload)
    result.metadata.update(
        {
            "llm_mode": "real",
            "llm_model": engine.agents[0].llm_client.model,
            "llm_base_url": engine.agents[0].llm_client.base_url,
        }
    )
    return result
