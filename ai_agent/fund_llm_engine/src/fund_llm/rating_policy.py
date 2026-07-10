import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Iterable, Tuple

from fund_llm import config
from fund_llm.contracts import AgentOutput, FundFeaturePack


ALL_RATING_AGENT_NAMES = (
    "PerformanceAgent",
    "ExposureAgent",
    "BondExposureAgent",
    "RiskAgent",
    "SentimentAgent",
    "SectorAgent",
    "MarketAgent",
)
CORE_RATING_AGENT_NAMES = frozenset({"PerformanceAgent", "RiskAgent"})

_ROUTED_AGENT_FLAGS = {
    "ExposureAgent": ("equity_exposure_applicable", True),
    "BondExposureAgent": ("bond_exposure_applicable", False),
    "SectorAgent": ("sector_analysis_applicable", True),
}


def expected_applicable_agent_names(features: FundFeaturePack) -> Tuple[str, ...]:
    """Return the fixed rating denominator after fund-type routing.

    Performance, Risk, Sentiment, and Market are conceptually applicable to all
    funds even when their current input is missing.  Exposure/Bond/Sector are
    removed only when deterministic routing marks them not applicable.
    """

    expected = []
    for agent_name in ALL_RATING_AGENT_NAMES:
        flag_config = _ROUTED_AGENT_FLAGS.get(agent_name)
        if flag_config is None:
            expected.append(agent_name)
            continue
        flag_name, default = flag_config
        if features.data_quality_flags.get(flag_name, default):
            expected.append(agent_name)
    return tuple(expected)


def is_valid_rating_score(value) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 100.0
    )


@dataclass(frozen=True)
class RatingCoverage:
    expected_agent_names: Tuple[str, ...]
    valid_outputs: Tuple[AgentOutput, ...]
    missing_agent_names: Tuple[str, ...]
    duplicate_agent_names: Tuple[str, ...]
    invalid_agent_names: Tuple[str, ...]
    unexpected_active_agent_names: Tuple[str, ...]

    @property
    def valid_agent_names(self) -> frozenset[str]:
        return frozenset(output.agent_name for output in self.valid_outputs)

    @property
    def scored_count(self) -> int:
        return len(self.valid_outputs)

    @property
    def applicable_count(self) -> int:
        return len(self.expected_agent_names)

    @property
    def ratio(self) -> float:
        return self.scored_count / self.applicable_count if self.applicable_count else 0.0

    @property
    def missing_core_agent_names(self) -> Tuple[str, ...]:
        return tuple(sorted(CORE_RATING_AGENT_NAMES - self.valid_agent_names))

    @property
    def policy_issue_agent_names(self) -> Tuple[str, ...]:
        return tuple(
            sorted(
                set(self.missing_agent_names)
                | set(self.duplicate_agent_names)
                | set(self.invalid_agent_names)
                | set(self.unexpected_active_agent_names)
            )
        )

    @property
    def meets_ratio(self) -> bool:
        threshold = Fraction(str(config.MIN_RATING_COVERAGE_RATIO))
        return (
            self.scored_count * threshold.denominator
            >= self.applicable_count * threshold.numerator
        )

    @property
    def quorum_met(self) -> bool:
        return (
            not self.missing_core_agent_names
            and self.scored_count >= config.MIN_RATING_AGENT_COUNT
            and self.meets_ratio
        )


def assess_rating_coverage(
    features: FundFeaturePack,
    agent_outputs: Iterable[AgentOutput],
) -> RatingCoverage:
    expected_names = expected_applicable_agent_names(features)
    expected_set = set(expected_names)
    known_set = set(ALL_RATING_AGENT_NAMES)
    grouped: Dict[str, list[AgentOutput]] = defaultdict(list)
    output_list = list(agent_outputs)
    for output in output_list:
        if output.agent_name in known_set:
            grouped[output.agent_name].append(output)

    duplicate_names = tuple(
        sorted(
            name
            for name, count in Counter(
                output.agent_name for output in output_list if output.agent_name in known_set
            ).items()
            if count > 1
        )
    )
    duplicate_set = set(duplicate_names)
    valid_outputs = []
    missing_names = []
    invalid_names = []

    for agent_name in expected_names:
        candidates = grouped.get(agent_name, [])
        if not candidates:
            missing_names.append(agent_name)
            continue
        if agent_name in duplicate_set:
            continue
        output = candidates[0]
        if output.status == "success" and is_valid_rating_score(output.score):
            valid_outputs.append(output)
        elif output.status == "success" or (
            output.status == "skipped" and output.stance == "not_applicable"
        ):
            invalid_names.append(agent_name)

    unexpected_active_names = []
    for agent_name in known_set - expected_set:
        for output in grouped.get(agent_name, []):
            if not (output.status == "skipped" and output.stance == "not_applicable"):
                unexpected_active_names.append(agent_name)
                break

    return RatingCoverage(
        expected_agent_names=expected_names,
        valid_outputs=tuple(valid_outputs),
        missing_agent_names=tuple(sorted(missing_names)),
        duplicate_agent_names=duplicate_names,
        invalid_agent_names=tuple(sorted(invalid_names)),
        unexpected_active_agent_names=tuple(sorted(unexpected_active_names)),
    )
