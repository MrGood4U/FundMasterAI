import logging

import pandas as pd

from daos.cache_dao import CacheDao, is_caching_enabled
from apis.akshare_public_fund_api import AksharePublicFund
from utils.kline_generator import KLineGenerator
from apis.efinance_api import EfinanceAPI

logger = logging.getLogger(__name__)

# cache-key templates — keyed by (platform, symbol)
_CACHE_KEYS = {
    # eastmoney
    ("eastmoney", "ETF"):       "fund:etf:spot",
    ("eastmoney", "LOF"):       "fund:lof:spot",
    # tonghuashun — all symbols hit the same underlying API
    #   ak.fund_etf_category_ths(symbol=...)
    ("tonghuashun", "all"):         "fund:cat:ths:all",
    ("tonghuashun", "stock"):       "fund:cat:ths:all",
    ("tonghuashun", "bond"):        "fund:cat:ths:all",
    ("tonghuashun", "mixed"):       "fund:cat:ths:all",
    ("tonghuashun", "ETF"):         "fund:cat:ths:all",
    ("tonghuashun", "LOF"):         "fund:cat:ths:all",
    ("tonghuashun", "QDII"):        "fund:cat:ths:all",
    ("tonghuashun", "hybrid"):      "fund:cat:ths:all",
    ("tonghuashun", "index"):       "fund:cat:ths:all",
    ("tonghuashun", "guaranteed"):  "fund:cat:ths:all",
}

# tonghuashun symbol → fund_type column value for client-side filtering
_THS_FUND_TYPE_MAP = {
    "stock":       "股票型",
    "bond":        "债券型",
    "mixed":       "混合型",
    "ETF":         "ETF",
    "LOF":         "LOF",
    "QDII":        "QDII",
    "guaranteed":  "保本型",
    "index":       "指数型",
    # "all" / "hybrid" — no filter, return all types
}


def _resolve_cache_key(platform: str, symbol: str) -> str | None:
    """Return the cache key for a given platform + symbol, or None."""
    return _CACHE_KEYS.get((platform, symbol))


def _filter_by_fund_type(df: "pd.DataFrame", platform: str, symbol: str) -> "pd.DataFrame":
    """Filter dataframe by fund_type column for tonghuashun requests.

    Only filters when *symbol* maps to a known fund_type.  Unknown symbols
    (like ``"all"``, ``"hybrid"``) pass through unfiltered.
    """
    if platform != "tonghuashun":
        return df
    fund_type = _THS_FUND_TYPE_MAP.get(symbol)
    if fund_type is None or "fund_type" not in df.columns:
        return df
    return df[df["fund_type"] == fund_type]


def _json_safe_records(df: "pd.DataFrame") -> list[dict]:
    """Return records that strict browser JSON parsers can consume."""
    clean = df.replace([float("inf"), float("-inf")], float("nan"))
    clean = clean.astype(object).where(pd.notna(clean), None)
    return clean.to_dict(orient="records")


class PublicFundService:
    def __init__(self):
        self.cache = CacheDao.from_config()
        self.efapi = EfinanceAPI()
        self.akapi = AksharePublicFund()

    # -- real-time (cached) ------------------------------------------------

    def get_one_real_time(self, name: str, code: str, platform: str, symbol: str):
        """Filter a single fund from the cached full list when possible."""
        cache_key = _resolve_cache_key(platform, symbol)
        df = None

        # 1. try cache (only if enabled in config.ini)
        if cache_key and is_caching_enabled(cache_key):
            df = self.cache.get_df(cache_key)

        # 2. fallback — always fetch "all" for tonghuashun so the cache
        #    stores the complete dataset, then filter client-side.
        if df is None or df.empty:
            fetch_symbol = "all" if platform == "tonghuashun" else symbol
            logger.info(
                "PublicFundService: cache miss for %s/%s, calling akshare",
                platform, symbol,
            )
            df = self.akapi.real_time(fetch_symbol, platform)
            if df is not None and not df.empty and cache_key and is_caching_enabled(cache_key):
                self.cache.set_df(cache_key, df)

        if df is None or df.empty:
            return [], (
                f"no data found for platform: {platform}, symbol: {symbol}"
            )

        # 3. filter by fund_type (tonghuashun only)
        df = _filter_by_fund_type(df, platform, symbol)

        data = _json_safe_records(df)
        if code:
            result = [
                item for item in data
                if item.get("code") == code or item.get("fund_code") == code
            ]
        elif name:
            result = [
                item for item in data
                if item.get("name") == name or item.get("fund_name") == name
            ]
        else:
            result = []

        if not result:
            return [], (
                f"no match found for code: {code} or name: {name} "
                f"in platform: {platform}, symbol: {symbol}"
            )
        return result, None

    def get_all_real_time(self, platform: str = None, symbol: str = None):
        """Return all real-time quotes for a fund type (cached)."""
        cache_key = _resolve_cache_key(platform, symbol)
        df = None

        if cache_key and is_caching_enabled(cache_key):
            df = self.cache.get_df(cache_key)

        if df is None or df.empty:
            # Always fetch "all" for tonghuashun so the cache stores the
            # complete dataset — filtering happens client-side afterwards.
            fetch_symbol = "all" if platform == "tonghuashun" else symbol
            logger.info(
                "PublicFundService: cache miss for %s/%s, calling akshare",
                platform, symbol,
            )
            df = self.akapi.real_time(fetch_symbol, platform)
            if df is not None and not df.empty and cache_key and is_caching_enabled(cache_key):
                self.cache.set_df(cache_key, df)

        if df is None or df.empty:
            return []

        # filter by fund_type (tonghuashun only — no-op for eastmoney)
        df = _filter_by_fund_type(df, platform, symbol)

        return _json_safe_records(df)

    # -- history / kline (not cached — per-fund, cheap) --------------------

    def get_hist(self, symbol: str, platform: str, code: str,
                 start_date: str, end_date: str, period: str, adjust: str):
        df = self.efapi.hist(code)
        if df is None or df.empty:
            return []
        if start_date:
            df["date"] = pd.to_datetime(df["date"])
            df = df.loc[df["date"] >= pd.to_datetime(start_date)]
        if end_date:
            df["date"] = pd.to_datetime(df["date"])
            df = df.loc[df["date"] <= pd.to_datetime(end_date)]
        if df.empty:
            return []
        return df.to_dict(orient="records")

    def get_hist_min(self, symbol: str, platform: str, code: str,
                     start_date: str, end_date: str, period: str, adjust: str):
        df = self.akapi.hist_min(symbol, platform, code,
                                 start_date, end_date, period, adjust)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_hist_kline(self, symbol: str, platform: str, code: str,
                       start_date: str, end_date: str,
                       period: str, adjust: str):
        df = self.efapi.hist(code)
        if df is None or df.empty:
            return []
        if start_date and end_date:
            df["date"] = pd.to_datetime(df["date"])
            mask = ((df["date"] >= pd.to_datetime(start_date)) &
                    (df["date"] <= pd.to_datetime(end_date)))
            df = df.loc[mask]
        if df.empty:
            return []
        gen = KLineGenerator(df, "unit_net_value")
        return gen.all().to_dict(orient="records")

    def get_hist_min_kline(self, symbol: str, platform: str, code: str,
                           start_date: str, end_date: str,
                           period: str, adjust: str):
        df = self.akapi.hist_min(symbol, platform, code,
                                 start_date, end_date, period, adjust)
        if df is None or df.empty:
            return []
        gen = KLineGenerator(df)
        return gen.all().to_dict(orient="records")

    # -- fund-name list (cached — rarely changes) ---------------------------

    def get_fund_name_list(self):
        cache_key = "fund:name:list"
        df = self.cache.get_df(cache_key)
        if df is None or df.empty:
            logger.info("PublicFundService: cache miss for fund_name_list")
            df = self.akapi.get_fund_name_list()
            if df is not None and not df.empty:
                self.cache.set_df(cache_key, df)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    # -- portfolio / analysis (per-fund, NOT cached) -----------------------

    def get_fund_portfolio_holds(self, code: str, year: str):
        df = self.akapi.get_fund_portfolio_holds(code, year)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_individual_analysis(self, code: str):
        df = self.akapi.get_fund_individual_analysis(code)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_individual_profit_probability(self, code: str):
        df = self.akapi.get_fund_individual_profit_probability(code)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    # -- value estimation (single — filter from cached "all") ---------------

    def get_fund_value_estimation(self, code: str, fund_type: str):
        cache_key = "fund:value:est:all"
        df = self.cache.get_df(cache_key)
        if df is None or df.empty:
            df = self.akapi.get_fund_value_estimation_list(fund_type)
            if df is not None and not df.empty:
                self.cache.set_df(cache_key, df)
        if df is None or df.empty:
            return []
        data = df.to_dict(orient="records")
        if code:
            return [
                item for item in data
                if item.get("code") == code or item.get("fund_code") == code
            ]
        return data

    def get_fund_value_estimation_list(self, fund_type: str):
        cache_key = "fund:value:est:all"
        df = self.cache.get_df(cache_key)
        if df is None or df.empty:
            df = self.akapi.get_fund_value_estimation_list(fund_type)
            if df is not None and not df.empty:
                self.cache.set_df(cache_key, df)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    # -- ranking (cached) --------------------------------------------------

    def fund_open_fund_rank(self, fund_type: str, order_by: str):
        cache_key = "fund:rank:" + fund_type
        df = self.cache.get_df(cache_key)
        if df is None or df.empty:
            # order_by doesn't matter for caching — we always sort
            # after retrieval so the cache is reusable across sort orders.
            df = self.akapi.fund_open_fund_rank(fund_type, order_by)
            if df is not None and not df.empty:
                self.cache.set_df(cache_key, df)
        if df is None or df.empty:
            return []
        # sort by the requested order_by column (descending)
        if order_by in df.columns:
            df = df.sort_values(by=order_by, ascending=False)
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    # -- index info (cached for "all" queries) ------------------------------

    def get_fund_info_index(self, symbol: str, indicator: str):
        cache_key = "fund:info:index:all"
        df = self.cache.get_df(cache_key)
        if df is None or df.empty:
            df = self.akapi.get_fund_info_index(symbol, indicator)
            if df is not None and not df.empty:
                self.cache.set_df(cache_key, df)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    # -- individual fund detail (per-fund, NOT cached) ---------------------

    def get_fund_individual_basic_info(self, code: str):
        df = self.akapi.get_fund_individual_basic_info(code)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_individual_detail_hold(self, code: str, date: str):
        df = self.akapi.get_fund_individual_detail_hold(code, date)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_portfolio_industry_allocation_em(self, code: str, year: str):
        result = self.akapi.get_fund_portfolio_industry_allocation_em(code, year)
        if isinstance(result, list) or result is None or result.empty:
            return []
        return result.to_dict(orient="records")

    def get_fund_portfolio_hold_stock(self, code: str, year: str):
        result = self.akapi.get_fund_portfolio_hold_stock(code, year)
        if isinstance(result, list) or result is None or result.empty:
            return []
        return result.to_dict(orient="records")

    def get_fund_portfolio_hold_bond(self, code: str, year: str):
        result = self.akapi.get_fund_portfolio_hold_bond(code, year)
        if isinstance(result, list) or result is None or result.empty:
            return []
        return result.to_dict(orient="records")
