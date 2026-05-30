import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fund_llm.agents import ChiefAgent, ExposureAgent, PerformanceAgent, RiskAgent, SectorAgent, SentimentAgent
from fund_llm.contracts import BenchmarkInfo, NavPoint
from fund_llm.feature_builder import FeatureBuilder
from fund_llm.llm_client import MockLLMClient
from fund_llm.mock_pipeline import build_mock_input


def build_long_nav_series(point_count: int, start_nav: float = 1.0) -> list[NavPoint]:
    nav = start_nav
    nav_series = []
    for day_index in range(point_count):
        nav_series.append(NavPoint(date=f"2026-03-{day_index + 1:03d}", nav=round(nav, 6)))
        if day_index % 2 == 0:
            nav *= 1.013
        else:
            nav *= 0.995
    return nav_series


def build_rich_input():
    payload = build_mock_input()
    payload.nav_series = build_long_nav_series(280)
    payload.benchmark = BenchmarkInfo(code="000300", name="沪深300", asset_type="index")
    payload.benchmark_nav_series = build_long_nav_series(280, start_nav=0.96)
    return payload


def main() -> None:
    features = FeatureBuilder().build(build_rich_input())
    llm_client = MockLLMClient("Mock upgraded agent narrative.")
    performance_output = PerformanceAgent(llm_client).analyze(features)
    exposure_output = ExposureAgent(llm_client).analyze(features)
    risk_output = RiskAgent(llm_client).analyze(features)
    sentiment_output = SentimentAgent(llm_client).analyze(features)
    sector_output = SectorAgent(llm_client).analyze(features)
    chief_output = ChiefAgent(llm_client).aggregate(
        features,
        [performance_output, exposure_output, risk_output, sentiment_output, sector_output],
    )

    outputs = {
        "performance_agent": performance_output.to_dict(),
        "exposure_agent": exposure_output.to_dict(),
        "risk_agent": risk_output.to_dict(),
        "sentiment_agent": sentiment_output.to_dict(),
        "sector_agent": sector_output.to_dict(),
        "chief_result": chief_output.to_dict(),
    }
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
