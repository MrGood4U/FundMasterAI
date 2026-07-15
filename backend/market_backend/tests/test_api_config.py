from apis import config as api_config


def test_fmp_key_prefers_primary_environment_variable(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "primary-key")
    monkeypatch.setenv("OPENBB_FMP_API_KEY", "compat-key")
    monkeypatch.setitem(api_config.config_dict["openbb"], "fmp_api_key", "file-key")

    assert api_config.get_openbb_fmp_api_key() == "primary-key"


def test_fmp_key_supports_compat_environment_variable(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.setenv("OPENBB_FMP_API_KEY", "compat-key")
    monkeypatch.setitem(api_config.config_dict["openbb"], "fmp_api_key", "file-key")

    assert api_config.get_openbb_fmp_api_key() == "compat-key"


def test_fmp_key_falls_back_to_config_file(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("OPENBB_FMP_API_KEY", raising=False)
    monkeypatch.setitem(api_config.config_dict["openbb"], "fmp_api_key", "file-key")

    assert api_config.get_openbb_fmp_api_key() == "file-key"
