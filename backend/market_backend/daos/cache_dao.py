"""Redis cache DAO — provides read/write for cached market data.

Data is stored as JSON (optionally gzip-compressed).  The service layer
reads from Redis first; if a key is missing or Redis is unreachable the
service falls back to a direct API call.
"""

from __future__ import annotations

import datetime as _dt
import gzip
import json
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import redis

from config import Config

logger = logging.getLogger(__name__)

# module-level flags — the first CacheDao instantiation probes Redis and
# records the result here so that every subsequent request skips the probe
# (and the warning log line).
_redis_available: bool = False   # True once a connection succeeds
_redis_checked: bool = False     # True after the *first* attempt (win or lose)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _json_default(obj: Any) -> Any:
    """Handle types that json.dumps can't serialise by default.

    - pandas NA / NaN       → None
    - pandas Timestamp       → ISO-8601 string
    - datetime.date / .datetime → ISO-8601 string
    - Decimal                → float
    - pandas Timedelta       → ISO-8601 duration string
    - bytes                  → UTF-8 string (or repr on failure)
    """
    if pd.isna(obj):
        return None
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, pd.Timedelta):
        return obj.isoformat()
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return repr(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ---------------------------------------------------------------------------
# CacheDao
# ---------------------------------------------------------------------------

class CacheDao:
    """Redis-backed cache for DataFrames / list-of-dicts market data."""

    # Default: compress payloads larger than 1 MiB
    DEFAULT_COMPRESSION_THRESHOLD = 1_048_576

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        compression_threshold: int = DEFAULT_COMPRESSION_THRESHOLD,
        compression_enabled: bool = True,
    ):
        self.compression_threshold = compression_threshold
        self.compression_enabled = compression_enabled
        self._password = password
        self._client: Optional[redis.Redis] = None

        global _redis_available, _redis_checked

        # If a previous CacheDao already probed Redis and it was down,
        # don't waste time trying again — stay silent.
        if _redis_checked and not _redis_available:
            return

        try:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password or None,
                decode_responses=False,
                socket_connect_timeout=3,
                socket_timeout=5,
            )
            self._client.ping()
            _redis_available = True
            logger.info("CacheDao: connected to Redis %s:%d/%d", host, port, db)
        except Exception:
            logger.warning(
                "CacheDao: Redis unreachable at %s:%d/%d — caching disabled",
                host, port, db,
            )
            self._client = None
        finally:
            _redis_checked = True

    # -- factory ----------------------------------------------------------

    @classmethod
    def from_config(cls) -> "CacheDao":
        """Build a CacheDao from the project Config object."""
        return cls(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            compression_threshold=Config.CACHE_COMPRESSION_THRESHOLD,
            compression_enabled=Config.CACHE_COMPRESSION,
        )

    # -- public API -------------------------------------------------------

    @property
    def available(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> Optional[List[Dict]]:
        """Return cached data as a list of dicts, or *None* on miss."""
        if not self._client:
            return None
        try:
            raw = self._client.get(key)
        except redis.RedisError as exc:
            logger.warning("CacheDao.get(%s) failed: %s", key, exc)
            return None

        if raw is None:
            return None

        # auto-detect gzip (magic bytes 1f 8b)
        if self.compression_enabled and raw[:2] == b"\x1f\x8b":
            try:
                raw = gzip.decompress(raw)
            except gzip.BadGzipFile:
                logger.warning("CacheDao.get(%s): bad gzip data, returning raw", key)
                # fall through — maybe it wasn't compressed

        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("CacheDao.get(%s): decode error — %s", key, exc)
            return None

    def set(
        self,
        key: str,
        data: List[Dict],
        ttl: Optional[int] = None,
    ) -> bool:
        """Write *data* (list of dicts) into Redis.  Returns True on success."""
        if not self._client:
            return False
        payload = json.dumps(
            data,
            ensure_ascii=False,
            default=_json_default,
        ).encode("utf-8")

        # json.dumps (allow_nan=True by default) emits NaN / Infinity /
        # -Infinity as JavaScript literals, which are not valid JSON.
        # Replace them with null so the stored payload is spec-compliant
        # and can be round-tripped by any JSON parser.
        # IMPORTANT: replace -Infinity *before* Infinity — otherwise
        # "-Infinity" becomes "-null" (invalid JSON).
        payload = (
            payload
            .replace(b"NaN", b"null")
            .replace(b"-Infinity", b"null")
            .replace(b"Infinity", b"null")
        )

        if self.compression_enabled and len(payload) > self.compression_threshold:
            payload = gzip.compress(payload, compresslevel=3)

        try:
            if ttl is not None and ttl > 0:
                self._client.setex(key, ttl, payload)
            else:
                self._client.set(key, payload)
        except redis.RedisError as exc:
            logger.warning("CacheDao.set(%s) failed: %s", key, exc)
            return False
        return True

    def get_df(self, key: str) -> Optional[pd.DataFrame]:
        """Like :meth:`get` but returns a DataFrame (or *None* on miss).

        Returns *None* immediately if caching is disabled for *key* in
        config.ini, so the caller falls back to the live API.
        """
        if not is_caching_enabled(key):
            return None
        data = self.get(key)
        if data is None:
            return None
        try:
            return pd.DataFrame(data)
        except Exception as exc:
            logger.warning("CacheDao.get_df(%s): %s", key, exc)
            return None

    def set_df(
        self,
        key: str,
        df: pd.DataFrame,
        ttl: Optional[int] = None,
    ) -> bool:
        """Write a DataFrame into Redis as JSON records.

        Silently returns *False* if caching is disabled for *key*.
        """
        if not is_caching_enabled(key):
            return False
        if df is None or df.empty:
            return False
        # Replace non-JSON-compliant float values with None.
        # pd.notna catches NaN/NaT; an extra replace step catches ±Inf.
        df_clean = df.copy()
        df_clean = df_clean.replace([np.inf, -np.inf, float("inf"), float("-inf")], None)
        df_clean = df_clean.where(pd.notna(df_clean), None)
        return self.set(key, df_clean.to_dict(orient="records"), ttl=ttl)

    def exists(self, key: str) -> bool:
        """Check whether *key* is present in Redis."""
        if not self._client:
            return False
        try:
            return bool(self._client.exists(key))
        except redis.RedisError:
            return False

    def delete(self, *keys: str) -> int:
        """Delete one or more keys.  Returns number of keys deleted."""
        if not self._client or not keys:
            return 0
        try:
            return self._client.delete(*keys)
        except redis.RedisError:
            return 0

    def ttl(self, key: str) -> int:
        """Remaining TTL in seconds (-1 = persistent, -2 = not found)."""
        if not self._client:
            return -2
        try:
            return self._client.ttl(key)
        except redis.RedisError:
            return -2

    def ping(self) -> bool:
        """True if Redis is reachable."""
        if not self._client:
            return False
        try:
            return self._client.ping()
        except redis.RedisError:
            return False


# ---------------------------------------------------------------------------
# Cache-control registry — maps cache keys to Config ENABLED flags
# ---------------------------------------------------------------------------

_CACHE_KEY_CONFIG_MAP: Dict[str, str] = {
    "stock:spot:em":        "CACHE_STOCK_SPOT_EM_ENABLED",
    "stock:spot:sina":      "CACHE_STOCK_SPOT_SINA_ENABLED",
    "fund:etf:spot":        "CACHE_FUND_ETF_SPOT_EM_ENABLED",
    "fund:lof:spot":        "CACHE_FUND_LOF_SPOT_EM_ENABLED",
    "fund:name:list":       "CACHE_FUND_NAME_LIST_ENABLED",
    "fund:rank:all":        "CACHE_FUND_RANK_ENABLED",
    "fund:cat:ths:all":     "CACHE_FUND_THS_SPOT_ENABLED",
    "fund:value:est:all":   "CACHE_FUND_VALUE_EST_ENABLED",
    "fund:info:index:all":  "CACHE_FUND_INFO_INDEX_ENABLED",
}


def is_caching_enabled(key: str) -> bool:
    """Return *True* if the given cache key is enabled in config.ini *and*
    Redis was reachable at startup.

    When Redis is unavailable the entire caching layer is disabled so that
    service code doesn't waste time trying cache reads/writes that would
    silently fail.  Unknown keys default to *False*.
    """
    if not _redis_available:
        return False
    attr = _CACHE_KEY_CONFIG_MAP.get(key)
    if attr is None:
        return False
    # Import here to avoid circular imports at module level.
    from config import Config
    return bool(getattr(Config, attr, False))
