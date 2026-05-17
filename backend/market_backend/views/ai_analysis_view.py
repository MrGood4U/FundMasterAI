from datetime import date, datetime
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = ROOT / "ai_agent" / "fund_llm_engine" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fund_llm.contracts import AnalysisWindow, FundAnalysisInput, FundInfo, NavPoint
from fund_llm.mock_pipeline import run_mock_analysis_for_input
from fund_llm.real_pipeline import run_real_analysis_for_input
from services.public_fund_service import PublicFundService

ai_analysis_bp = Blueprint("ai_analysis", __name__, url_prefix="/api/ai")


def _to_iso_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return ""
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    if "," in text and "GMT" in text:
        try:
            return parsedate_to_datetime(text).date().isoformat()
        except (TypeError, ValueError):
            return text
    return text[:10]


def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pick_first(payload: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None and value != "":
            return value
    return None


def _build_nav_series(
    records: List[Dict[str, Any]],
    start_date: Optional[str],
    end_date: Optional[str],
    max_points: int,
) -> List[NavPoint]:
    points = []
    for item in records:
        point_date = _to_iso_date(_pick_first(item, ["净值日期", "日期", "date", "数据日期"]))
        nav = _to_float(_pick_first(item, ["单位净值", "累计净值", "收盘", "最新价", "nav"]))
        if not point_date or nav is None:
            continue
        if start_date and point_date < start_date:
            continue
        if end_date and point_date > end_date:
            continue
        points.append(NavPoint(date=point_date, nav=nav))

    points.sort(key=lambda point: point.date)
    if max_points > 0:
        points = points[-max_points:]
    return points


@lru_cache(maxsize=1)
def _fund_name_records() -> List[Dict[str, Any]]:
    return PublicFundService().get_fund_name_list()


def _lookup_fund_info(code: str, requested_name: str = "") -> FundInfo:
    matched = None
    try:
        matched = next(
            (item for item in _fund_name_records() if str(item.get("基金代码", "")) == code),
            None,
        )
    except Exception:
        matched = None

    return FundInfo(
        code=code,
        name=str((matched or {}).get("基金简称") or requested_name or code),
        asset_type="fund_open",
        category=str((matched or {}).get("基金类型") or "unknown"),
        manager=None,
    )


def _build_analysis_input(data: Dict[str, Any]) -> tuple[FundAnalysisInput, Dict[str, Any]]:
    code = str(data.get("code") or "005827").strip()
    start_date = data.get("start_date") or "2025-01-01"
    end_date = data.get("end_date")
    max_points = int(data.get("max_nav_points") or 260)

    service = PublicFundService()
    nav_records = service.get_open_fund_nav(code)
    nav_series = _build_nav_series(nav_records, start_date, end_date, max_points)
    if not nav_series:
        raise ValueError(f"No nav_series data returned for fund code {code}.")

    fund_info = _lookup_fund_info(code, str(data.get("name") or ""))
    analysis_window = AnalysisWindow(
        start_date=nav_series[0].date,
        end_date=nav_series[-1].date,
        as_of_date=nav_series[-1].date,
    )
    payload = FundAnalysisInput(
        request_id=f"real-backend-{code}-{analysis_window.as_of_date}",
        fund_info=fund_info,
        nav_series=nav_series,
        analysis_window=analysis_window,
        fund_tags=["backend-data", "open-fund"],
        extra_context={
            "data_source": "market_backend.akshare",
            "client_risk_profile": str(data.get("client_risk_profile") or "balanced"),
        },
    )
    source = {
        "fund_code": code,
        "fund_name": fund_info.name,
        "fund_category": fund_info.category,
        "raw_nav_count": len(nav_records),
        "used_nav_count": len(nav_series),
        "start_date": analysis_window.start_date,
        "end_date": analysis_window.end_date,
        "known_gaps": [
            "industry_exposure",
            "top_holdings_weight",
            "benchmark_nav_series",
            "fund_manager",
            "fund_size",
        ],
    }
    return payload, source


@ai_analysis_bp.post("/fund/analyze")
def analyze_fund():
    data = request.get_json(silent=True) or {}
    try:
        payload, source = _build_analysis_input(data)
        llm_mode = str(data.get("llm_mode") or "mock").strip().lower()
        if llm_mode == "real":
            result = run_real_analysis_for_input(payload, max_parallel_agents=3)
        else:
            result = run_mock_analysis_for_input(
                payload,
                mock_response="Real backend data was transformed and analyzed by the FundMaster engine.",
                max_parallel_agents=5,
            )
            result.metadata["llm_mode"] = "mock"
        result.metadata["data_mode"] = "real_backend"
        result.metadata["nav_point_count"] = str(source["used_nav_count"])
    except (RuntimeError, ValueError) as exc:
        return jsonify({"code": 502, "message": str(exc), "data": None}), 502
    except Exception as exc:
        return jsonify({"code": 500, "message": f"analysis failed: {exc}", "data": None}), 500

    return jsonify(
        {
            "code": 200,
            "message": "success",
            "data": {
                "analysis": result.to_dict(),
                "input": payload.to_dict(),
                "source": source,
            },
        }
    ), 200
