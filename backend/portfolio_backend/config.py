import os
import configparser

_ini = configparser.ConfigParser()
_ini_path = os.path.join(os.path.dirname(__file__), "config.ini")
_ini.read(_ini_path)


def _get(section, key, default, type_fn=str):
    # 1. env var (highest)
    env_val = os.environ.get(key)
    if env_val is not None:
        return type_fn(env_val)
    # 2. config.ini
    try:
        ini_val = _ini.get(section, key)
        if ini_val:
            return type_fn(ini_val)
    except (configparser.NoSectionError, configparser.NoOptionError):
        pass
    # 3. hardcoded default (lowest)
    return type_fn(default)


class Config:
    SECRET_KEY = _get("app", "SECRET_KEY", "a_very_secret_key_that_should_be_changed")

    # MySQL
    MYSQL_HOST = _get("mysql", "MYSQL_HOST", "localhost")
    MYSQL_USER = _get("mysql", "MYSQL_USER", "root")
    MYSQL_PORT = _get("mysql", "MYSQL_PORT", 3306, type_fn=int)
    MYSQL_PASSWORD = _get("mysql", "MYSQL_PASSWORD", "password")
    MYSQL_DB = _get("mysql", "MYSQL_DB", "fundmaster_db")

    # Redis
    REDIS_HOST = _get("redis", "REDIS_HOST", "localhost")
    REDIS_PORT = _get("redis", "REDIS_PORT", 6379, type_fn=int)
    REDIS_DB = _get("redis", "REDIS_DB", 0, type_fn=int)

    # HTTP
    HTTP_PORT = _get("app", "PORTFOLIO_HTTP_PORT", 5002, type_fn=int)

    # Alert checker
    ALERT_CHECK_INTERVAL_MINUTES = _get("app", "ALERT_CHECK_INTERVAL_MINUTES", 5, type_fn=int)

    # Internal service URLs
    MARKET_BACKEND_URL = _get("market_backend", "MARKET_BACKEND_URL", "http://localhost:5001")
