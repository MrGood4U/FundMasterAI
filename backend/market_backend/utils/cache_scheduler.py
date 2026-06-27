"""Background cache refresher — periodically calls slow akshare APIs and
writes the results into Redis so the web tier responds in milliseconds.

Usage (from app.py)::

    from utils.cache_scheduler import CacheScheduler
    scheduler = CacheScheduler(cache_dao=app.config["cache_dao"])
    scheduler.start()
    # ...
    scheduler.stop()
"""

from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from typing import Callable, Dict

from daos.cache_dao import CacheDao
from config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fetcher helpers (module-level so they are pickleable for ThreadPoolExecutor)
# ---------------------------------------------------------------------------

def _fetch_stock_spot_em():
    from apis.akshare_stock_api import AkshareStock
    return AkshareStock().eastmoney_a_spot_all()


def _fetch_stock_spot_sina():
    from apis.akshare_stock_api import AkshareStock
    return AkshareStock().sina_a_spot_all()


def _fetch_fund_etf_spot():
    from apis.akshare_public_fund_api import AksharePublicFund
    return AksharePublicFund().eastmoney_real_time("ETF")


def _fetch_fund_lof_spot():
    from apis.akshare_public_fund_api import AksharePublicFund
    return AksharePublicFund().eastmoney_real_time("LOF")


def _fetch_fund_name_list():
    from apis.akshare_public_fund_api import AksharePublicFund
    return AksharePublicFund().get_fund_name_list()


def _fetch_fund_rank_all():
    from apis.akshare_public_fund_api import AksharePublicFund
    return AksharePublicFund().fund_open_fund_rank("all")


def _fetch_fund_category_ths_all():
    from apis.akshare_public_fund_api import AksharePublicFund
    return AksharePublicFund().tonghuashun_real_time("all")


def _fetch_fund_value_est_all():
    from apis.akshare_public_fund_api import AksharePublicFund
    return AksharePublicFund().get_fund_value_estimation_list("all")


def _fetch_fund_info_index_all():
    from apis.akshare_public_fund_api import AksharePublicFund
    return AksharePublicFund().get_fund_info_index("all", "all")


# -- registry --------------------------------------------------------------
# Each entry maps a cache key to the callable that fetches fresh data.

_DEFAULT_REGISTRY: Dict[str, Callable] = {
    "stock:spot:em":            _fetch_stock_spot_em,
    "stock:spot:sina":          _fetch_stock_spot_sina,
    "fund:etf:spot":            _fetch_fund_etf_spot,
    "fund:lof:spot":            _fetch_fund_lof_spot,
    "fund:name:list":           _fetch_fund_name_list,
    "fund:rank:all":            _fetch_fund_rank_all,
    "fund:cat:ths:all":         _fetch_fund_category_ths_all,
    "fund:value:est:all":       _fetch_fund_value_est_all,
    "fund:info:index:all":      _fetch_fund_info_index_all,
}

# mapping from cache key → (enabled_attr, interval_attr)
_KEY_CONFIG: Dict[str, tuple] = {
    "stock:spot:em":       ("CACHE_STOCK_SPOT_EM_ENABLED",       "CACHE_STOCK_SPOT_EM_INTERVAL"),
    "stock:spot:sina":     ("CACHE_STOCK_SPOT_SINA_ENABLED",     "CACHE_STOCK_SPOT_SINA_INTERVAL"),
    "fund:etf:spot":       ("CACHE_FUND_ETF_SPOT_EM_ENABLED",    "CACHE_FUND_ETF_SPOT_EM_INTERVAL"),
    "fund:lof:spot":       ("CACHE_FUND_LOF_SPOT_EM_ENABLED",    "CACHE_FUND_LOF_SPOT_EM_INTERVAL"),
    "fund:name:list":      ("CACHE_FUND_NAME_LIST_ENABLED",      "CACHE_FUND_NAME_LIST_INTERVAL"),
    "fund:rank:all":       ("CACHE_FUND_RANK_ENABLED",           "CACHE_FUND_RANK_INTERVAL"),
    "fund:cat:ths:all":    ("CACHE_FUND_THS_SPOT_ENABLED",   "CACHE_FUND_THS_SPOT_INTERVAL"),
    "fund:value:est:all":  ("CACHE_FUND_VALUE_EST_ENABLED",      "CACHE_FUND_VALUE_EST_INTERVAL"),
    "fund:info:index:all": ("CACHE_FUND_INFO_INDEX_ENABLED",     "CACHE_FUND_INFO_INDEX_INTERVAL"),
}


# ---------------------------------------------------------------------------
# CacheScheduler
# ---------------------------------------------------------------------------

class CacheScheduler:
    """Periodically refresh slow akshare datasets into Redis.

    Runs a daemon thread that:
    1. On :meth:`start`: warms *all* registered keys eagerly.
    2. Then loops, submitting refresh jobs to a thread-pool whenever a
       key's interval has passed.  A key is never refreshed twice
       concurrently — if the previous refresh is still in flight the
       scheduler skips it until the next tick.
    """

    def __init__(self, cache_dao: CacheDao):
        self.cache = cache_dao
        self.intervals = _build_intervals()

        # {key: last_finish_timestamp}
        self._last_finished: Dict[str, float] = {}
        # keys currently being refreshed
        self._in_flight: Dict[str, bool] = {k: False for k in self.intervals}

        self._stop_event = threading.Event()
        self._executor: concurrent.futures.ThreadPoolExecutor | None = None
        self._thread: threading.Thread | None = None

    # -- public -------------------------------------------------------------

    def start(self) -> None:
        """Warm the cache synchronously, then start the background loop."""
        if not self.cache.available:
            logger.warning(
                "CacheScheduler: Redis unavailable — scheduler disabled"
            )
            return

        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="cache-sched"
        )

        self._warm_all()

        self._thread = threading.Thread(
            target=self._run, name="cache-scheduler", daemon=True
        )
        self._thread.start()
        logger.info("CacheScheduler: started (%d keys)", len(self.intervals))

    def stop(self) -> None:
        """Signal the background loop to exit and wait for running jobs."""
        logger.info("CacheScheduler: stopping...")
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
        logger.info("CacheScheduler: stopped")

    # -- internals ----------------------------------------------------------

    def _warm_all(self) -> None:
        """Fetch every enabled key in parallel, then wait for all to finish."""
        logger.info(
            "CacheScheduler: warming %d keys in parallel ...", len(self.intervals)
        )
        futures = {}
        for key in self.intervals:
            self._in_flight[key] = True
            futures[self._executor.submit(self._refresh_key, key)] = key  # type: ignore[union-attr]

        for f in futures:
            key = futures[f]
            try:
                f.result()
            except Exception:
                logger.exception("CacheScheduler: %s warm-up failed", key)
        logger.info("CacheScheduler: warm-up complete")

    def _run(self) -> None:
        check_interval = 2  # seconds between loop ticks
        while not self._stop_event.is_set():
            now = time.time()
            for key in list(self.intervals):
                interval = self.intervals[key]
                last = self._last_finished.get(key, 0)
                if now - last < interval:
                    continue
                if self._in_flight.get(key, False):
                    continue
                self._in_flight[key] = True
                self._executor.submit(self._refresh_key, key)  # type: ignore[union-attr]
            self._stop_event.wait(check_interval)

    def _refresh_key(self, key: str) -> None:
        """Fetch and cache a single key (used by warm-up and periodic loop)."""
        try:
            fetcher = _DEFAULT_REGISTRY[key]
            logger.info("CacheScheduler: refreshing %s ...", key)
            df = fetcher()
            if df is not None and not df.empty:
                ok = self.cache.set_df(key, df)
                if ok:
                    self._last_finished[key] = time.time()
                    logger.info(
                        "CacheScheduler: %s → cache (%d rows)", key, len(df)
                    )
                else:
                    logger.warning("CacheScheduler: %s cache write failed", key)
            else:
                logger.warning("CacheScheduler: %s returned empty data", key)
        except Exception:
            logger.exception("CacheScheduler: %s refresh failed", key)
        finally:
            self._in_flight[key] = False


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _build_intervals() -> Dict[str, int]:
    """Read intervals from Config for *enabled* keys only.

    Disabled keys are silently excluded — the scheduler won't warm or
    refresh them, and the service layer should also skip cache lookups.
    """
    intervals: Dict[str, int] = {}
    for key, (enabled_attr, interval_attr) in _KEY_CONFIG.items():
        if not getattr(Config, enabled_attr, False):
            continue
        intervals[key] = int(getattr(Config, interval_attr, 60))
    return intervals
