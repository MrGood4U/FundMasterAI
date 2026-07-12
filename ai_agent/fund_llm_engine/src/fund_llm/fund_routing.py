from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterable, Set

if TYPE_CHECKING:
    from fund_llm.contracts import FundAnalysisInput


AVAILABLE = "available"
MISSING = "missing"
MISSING_BACKEND_CAPABILITY = "missing_backend_capability"
NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class FundTypeProfile:
    raw_type: str
    normalized_type: str
    family: str
    equity_exposure_applicable: bool
    sector_analysis_applicable: bool
    bond_exposure_applicable: bool
    asset_allocation_required: bool

    @property
    def is_bond_like(self) -> bool:
        return self.family == "bond"


def _normalize_text(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "")


def classify_fund_type(raw_type: str) -> FundTypeProfile:
    """Map backend fund_type text into deterministic routing flags.

    The LLM should not decide fund type. This function intentionally uses only
    structured backend text and conservative keyword rules.
    """

    text = _normalize_text(raw_type)
    if not text or text == "unknown":
        return FundTypeProfile(
            raw_type=raw_type or "unknown",
            normalized_type="unknown_fund",
            family="unknown",
            equity_exposure_applicable=True,
            sector_analysis_applicable=True,
            bond_exposure_applicable=False,
            asset_allocation_required=False,
        )

    if "货币" in text or "money" in text:
        return FundTypeProfile(
            raw_type=raw_type,
            normalized_type="money_market_fund",
            family="money_market",
            equity_exposure_applicable=False,
            sector_analysis_applicable=False,
            bond_exposure_applicable=True,
            asset_allocation_required=True,
        )

    if "qdii" in text:
        return FundTypeProfile(
            raw_type=raw_type,
            normalized_type="qdii_fund",
            family="qdii",
            equity_exposure_applicable=True,
            sector_analysis_applicable=True,
            bond_exposure_applicable=False,
            asset_allocation_required=False,
        )

    if "fof" in text:
        return FundTypeProfile(
            raw_type=raw_type,
            normalized_type="fof_fund",
            family="fof",
            equity_exposure_applicable=False,
            sector_analysis_applicable=False,
            bond_exposure_applicable=False,
            asset_allocation_required=True,
        )

    compact_text = text.replace("_", "").replace("-", "")
    if "债券" in text or "bond" in text or "固收" in text or "fixedincome" in compact_text:
        normalized_type = "bond_index_fund" if "指数" in text or "index" in text else "bond_fund"
        return FundTypeProfile(
            raw_type=raw_type,
            normalized_type=normalized_type,
            family="bond",
            equity_exposure_applicable=False,
            sector_analysis_applicable=False,
            bond_exposure_applicable=True,
            asset_allocation_required=True,
        )

    if "混合" in text or "mixed" in text:
        return FundTypeProfile(
            raw_type=raw_type,
            normalized_type="mixed_fund",
            family="equity_like",
            equity_exposure_applicable=True,
            sector_analysis_applicable=True,
            bond_exposure_applicable=False,
            asset_allocation_required=False,
        )

    if "指数" in text or "index" in text:
        return FundTypeProfile(
            raw_type=raw_type,
            normalized_type="stock_index_fund",
            family="equity_like",
            equity_exposure_applicable=True,
            sector_analysis_applicable=True,
            bond_exposure_applicable=False,
            asset_allocation_required=False,
        )

    if "股票" in text or "equity" in text or "stock" in text:
        return FundTypeProfile(
            raw_type=raw_type,
            normalized_type="equity_fund",
            family="equity_like",
            equity_exposure_applicable=True,
            sector_analysis_applicable=True,
            bond_exposure_applicable=False,
            asset_allocation_required=False,
        )

    return FundTypeProfile(
        raw_type=raw_type,
        normalized_type="unknown_fund",
        family="unknown",
        equity_exposure_applicable=True,
        sector_analysis_applicable=True,
        bond_exposure_applicable=False,
        asset_allocation_required=False,
    )


def resolve_equity_analysis_applicability(
    payload: "FundAnalysisInput",
    profile: FundTypeProfile | None = None,
) -> tuple[bool, bool]:
    """Combine conservative type defaults with disclosed equity evidence.

    ``top_holdings_weight`` is deliberately not sufficient evidence by itself:
    legacy bond inputs may use that aggregate for bond positions. Structured
    stock-holding rows or an industry breakdown are unambiguous equity evidence.
    """

    profile = profile or classify_fund_type(payload.fund_info.category)
    has_disclosed_equity_data = bool(payload.top_holdings) or bool(
        payload.industry_exposure
    )
    return (
        profile.equity_exposure_applicable or has_disclosed_equity_data,
        profile.sector_analysis_applicable or has_disclosed_equity_data,
    )


def parse_tool_names(value: str | Iterable[str] | None) -> Set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return set()
        if text.startswith("["):
            try:
                decoded = json.loads(text)
                if isinstance(decoded, list):
                    return {str(item) for item in decoded}
            except json.JSONDecodeError:
                pass
        return {item.strip() for item in text.split(",") if item.strip()}
    return {str(item) for item in value if str(item).strip()}


def _is_backend_registry_payload(payload: "FundAnalysisInput") -> bool:
    return payload.extra_context.get("data_source") == "backend_function_registry"


def _has_any_tool(available_tools: Set[str], names: Iterable[str]) -> bool:
    return any(name in available_tools for name in names)


def _missing_status(payload: "FundAnalysisInput", available_tools: Set[str], tool_names: Iterable[str]) -> str:
    if _is_backend_registry_payload(payload) and not _has_any_tool(available_tools, tool_names):
        return MISSING_BACKEND_CAPABILITY
    return MISSING


def _has_positive_count(payload: "FundAnalysisInput", key: str) -> bool:
    try:
        return int(payload.extra_context.get(key, "0") or "0") > 0
    except ValueError:
        return False


def _has_bond_holdings(payload: "FundAnalysisInput") -> bool:
    return bool(getattr(payload, "bond_holdings", [])) or _has_positive_count(payload, "bond_holdings_count")


def _has_asset_allocation(payload: "FundAnalysisInput") -> bool:
    return (
        bool(getattr(payload, "asset_allocation", {}))
        or int(getattr(payload, "invalid_asset_allocation_count", 0) or 0) > 0
        or _has_positive_count(payload, "asset_allocation_count")
    )


def build_data_coverage(payload: "FundAnalysisInput") -> Dict[str, str]:
    profile = classify_fund_type(payload.fund_info.category)
    equity_exposure_applicable, sector_analysis_applicable = (
        resolve_equity_analysis_applicability(payload, profile)
    )
    available_tools = parse_tool_names(payload.extra_context.get("available_backend_tools"))

    coverage = {
        "fund_type": AVAILABLE if profile.normalized_type != "unknown_fund" else MISSING,
        "nav": AVAILABLE if payload.nav_series else MISSING,
        "basic_info": AVAILABLE if payload.fund_info.category and payload.fund_info.category != "unknown" else MISSING,
        "news_signal": AVAILABLE if payload.news_summary or payload.news_items else MISSING,
    }

    if equity_exposure_applicable:
        coverage["stock_holdings"] = (
            AVAILABLE
            if payload.top_holdings_weight is not None
            else _missing_status(
                payload,
                available_tools,
                ["get_fund_portfolio_holds", "get_fund_portfolio_hold_stock"],
            )
        )
    else:
        coverage["stock_holdings"] = NOT_APPLICABLE

    if sector_analysis_applicable:
        coverage["industry_exposure"] = (
            AVAILABLE
            if payload.industry_exposure
            else _missing_status(
                payload,
                available_tools,
                ["get_fund_industry_allocation", "get_fund_portfolio_industry_allocation"],
            )
        )
    else:
        coverage["industry_exposure"] = NOT_APPLICABLE

    if profile.bond_exposure_applicable:
        coverage["bond_holdings"] = (
            AVAILABLE
            if _has_bond_holdings(payload)
            else _missing_status(
                payload,
                available_tools,
                [
                    "get_fund_bond_holdings",
                    "get_fund_portfolio_bond_holdings",
                    "get_fund_portfolio_hold_bond",
                ],
            )
        )
    else:
        coverage["bond_holdings"] = NOT_APPLICABLE

    if profile.asset_allocation_required:
        coverage["asset_allocation"] = (
            AVAILABLE
            if _has_asset_allocation(payload)
            else _missing_status(
                payload,
                available_tools,
                [
                    "get_fund_asset_allocation",
                    "get_fund_hold_structure",
                    "get_fund_individual_detail_hold",
                ],
            )
        )
    else:
        coverage["asset_allocation"] = NOT_APPLICABLE

    return coverage
