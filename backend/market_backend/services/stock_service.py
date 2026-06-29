import logging

import pandas as pd

from daos.cache_dao import CacheDao, is_caching_enabled
from apis.akshare_stock_api import AkshareStock
from utils.kline_generator import KLineGenerator

logger = logging.getLogger(__name__)

# cache-key → platform mapping used by "all spot" endpoints
_SPOT_CACHE_KEYS = {
    "eastmoney": "stock:spot:em",
    "sina":      "stock:spot:sina",
}


class StockService:
    def __init__(self):
        self.cache = CacheDao.from_config()
        self.akapi = AkshareStock()

    # -- spot --------------------------------------------------------------

    def get_all_a_spot(self, platform: str):
        """Return every A-share stock's latest quote (cached if enabled)."""
        cache_key = _SPOT_CACHE_KEYS.get(platform)
        df = None

        # 1. try cache (only if enabled in config.ini)
        if cache_key and is_caching_enabled(cache_key):
            df = self.cache.get_df(cache_key)

        # 2. fallback — direct API call + backfill cache
        if df is None or df.empty:
            logger.info("StockService: cache miss for %s, calling akshare", platform)
            df = self.akapi.a_spot_all(platform)
            if df is not None and not df.empty and cache_key and is_caching_enabled(cache_key):
                self.cache.set_df(cache_key, df)

        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_a_spot(self, platform: str, code: str, name: str):
        """Return a single stock's quote — filters from the cached full list
        when caching is enabled, otherwise calls the API directly."""
        cache_key = _SPOT_CACHE_KEYS.get(platform)

        # 1. try cache — load all, filter in-memory (microseconds)
        if cache_key and is_caching_enabled(cache_key):
            df = self.cache.get_df(cache_key)
            if df is not None and not df.empty:
                if code:
                    col = "stock_code" if "stock_code" in df.columns else "code"
                    matched = df[df[col] == code]
                elif name:
                    col = "stock_name" if "stock_name" in df.columns else "name"
                    matched = df[df[col].str.contains(name, na=False)]
                else:
                    return []
                return matched.to_dict(orient="records")

        # 2. fallback
        df = self.akapi.a_spot_one(platform, code, name)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    # -- history / bid-ask / kline (not cached — per-stock, cheap) --------

    def get_a_hist(self, platform: str, code: str, period: str,
                   start_date: str, end_date: str, adjust: str):
        df = self.akapi.a_hist(platform, code, period,
                               start_date, end_date, adjust)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_a_bid_ask(self, platform: str, code: str):
        df = self.akapi.a_bid_ask(platform, code)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_a_hist_kline(self, platform: str, code: str, period: str,
                         start_date: str, end_date: str, adjust: str):
        df = self.akapi.a_hist(platform, code, period,
                               start_date, end_date, adjust)
        if df is None or df.empty:
            return []
        gen = KLineGenerator(df)
        return gen.all().to_dict(orient="records")