import os
from configparser import ConfigParser


def _read_ini_config():
    """Read [cache] and [redis] sections from apis/config.ini, returning a
    merged dict with sensible defaults for every key."""
    ini_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "apis", "config.ini"
    )
    defaults = {
        # -- [cache] section --
        "STOCK_SPOT_EM_ENABLED": "false",
        "STOCK_SPOT_EM_INTERVAL": "120",
        "STOCK_SPOT_SINA_ENABLED": "false",
        "STOCK_SPOT_SINA_INTERVAL": "600",
        "FUND_ETF_SPOT_EM_ENABLED": "false",
        "FUND_ETF_SPOT_EM_INTERVAL": "30",
        "FUND_LOF_SPOT_EM_ENABLED": "false",
        "FUND_LOF_SPOT_EM_INTERVAL": "30",
        "FUND_NAME_LIST_ENABLED": "false",
        "FUND_NAME_LIST_INTERVAL": "3600",
        "FUND_RANK_ENABLED": "false",
        "FUND_RANK_INTERVAL": "60",
        "FUND_THS_SPOT_ENABLED": "false",
        "FUND_THS_SPOT_INTERVAL": "60",
        "FUND_VALUE_EST_ENABLED": "false",
        "FUND_VALUE_EST_INTERVAL": "30",
        "FUND_INFO_INDEX_ENABLED": "false",
        "FUND_INFO_INDEX_INTERVAL": "60",
        "GLOBAL_INDEX_RANK_ENABLED": "false",
        "GLOBAL_INDEX_RANK_INTERVAL": "600",
        "COMPRESSION_THRESHOLD": "1048576",
        "COMPRESSION": "false",
        # -- [redis] section --
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "0",
        "REDIS_PASSWORD": "",
    }
    cp = ConfigParser()
    cp.read(ini_path)

    # read every key from whichever section it belongs to
    section_map = {
        "cache": {k for k in defaults if not k.startswith("REDIS_")},
        "redis": {k for k in defaults if k.startswith("REDIS_")},
    }
    result = {}
    for section, keys in section_map.items():
        for key in keys:
            if cp.has_section(section):
                result[key] = cp.get(section, key, fallback=defaults[key])
            else:
                result[key] = defaults[key]
    return result


_ini = _read_ini_config()


def _bool(v: str) -> bool:
    return v.lower() in ("true", "1", "yes")


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_that_should_be_changed'

    # MySQL Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'password'
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'fundmaster_db'

    # Redis Configuration — priority: config.ini > env > default
    REDIS_HOST = _ini.get("REDIS_HOST") or os.environ.get("REDIS_HOST") or "localhost"
    REDIS_PORT = int(_ini.get("REDIS_PORT") or os.environ.get("REDIS_PORT") or 6379)
    REDIS_DB = int(_ini.get("REDIS_DB") or os.environ.get("REDIS_DB") or 0)

    # Http Configuration
    HTTP_PORT = int(os.environ.get('MARKET_HTTP_PORT') or 5001)

    # Cache Configuration (read from apis/config.ini)
    CACHE_STOCK_SPOT_EM_ENABLED = _bool(_ini["STOCK_SPOT_EM_ENABLED"])
    CACHE_STOCK_SPOT_EM_INTERVAL = int(_ini["STOCK_SPOT_EM_INTERVAL"])
    CACHE_STOCK_SPOT_SINA_ENABLED = _bool(_ini["STOCK_SPOT_SINA_ENABLED"])
    CACHE_STOCK_SPOT_SINA_INTERVAL = int(_ini["STOCK_SPOT_SINA_INTERVAL"])
    CACHE_FUND_ETF_SPOT_EM_ENABLED = _bool(_ini["FUND_ETF_SPOT_EM_ENABLED"])
    CACHE_FUND_ETF_SPOT_EM_INTERVAL = int(_ini["FUND_ETF_SPOT_EM_INTERVAL"])
    CACHE_FUND_LOF_SPOT_EM_ENABLED = _bool(_ini["FUND_LOF_SPOT_EM_ENABLED"])
    CACHE_FUND_LOF_SPOT_EM_INTERVAL = int(_ini["FUND_LOF_SPOT_EM_INTERVAL"])
    CACHE_FUND_NAME_LIST_ENABLED = _bool(_ini["FUND_NAME_LIST_ENABLED"])
    CACHE_FUND_NAME_LIST_INTERVAL = int(_ini["FUND_NAME_LIST_INTERVAL"])
    CACHE_FUND_RANK_ENABLED = _bool(_ini["FUND_RANK_ENABLED"])
    CACHE_FUND_RANK_INTERVAL = int(_ini["FUND_RANK_INTERVAL"])
    CACHE_FUND_THS_SPOT_ENABLED = _bool(_ini["FUND_THS_SPOT_ENABLED"])
    CACHE_FUND_THS_SPOT_INTERVAL = int(_ini["FUND_THS_SPOT_INTERVAL"])
    CACHE_FUND_VALUE_EST_ENABLED = _bool(_ini["FUND_VALUE_EST_ENABLED"])
    CACHE_FUND_VALUE_EST_INTERVAL = int(_ini["FUND_VALUE_EST_INTERVAL"])
    CACHE_FUND_INFO_INDEX_ENABLED = _bool(_ini["FUND_INFO_INDEX_ENABLED"])
    CACHE_FUND_INFO_INDEX_INTERVAL = int(_ini["FUND_INFO_INDEX_INTERVAL"])
    CACHE_GLOBAL_INDEX_RANK_ENABLED = _bool(_ini["GLOBAL_INDEX_RANK_ENABLED"])
    CACHE_GLOBAL_INDEX_RANK_INTERVAL = int(_ini["GLOBAL_INDEX_RANK_INTERVAL"])
    CACHE_COMPRESSION_THRESHOLD = int(_ini["COMPRESSION_THRESHOLD"])
    CACHE_COMPRESSION = _bool(_ini["COMPRESSION"])
