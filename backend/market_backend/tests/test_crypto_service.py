import pytest
from unittest.mock import MagicMock, patch

from services.crypto_service import CryptoService


@pytest.fixture
def service():
    with patch("apis.okx_api.config") as mock_config:
        mock_config.get_okx_api_key.return_value = "test_key"
        mock_config.get_okx_api_secret.return_value = "test_secret"
        mock_config.get_okx_api_pass.return_value = "test_pass"

        with patch("apis.okx_api.Account"), patch("apis.okx_api.OkxSPOT"):
            return CryptoService()


class TestGetBooks:
    def test_delegates_to_okx(self, service, sample_crypto_books):
        service.okx.get_books = MagicMock(return_value=sample_crypto_books)
        result = service.get_books("BTC")
        service.okx.get_books.assert_called_once_with("BTC")
        assert result == sample_crypto_books


class TestGetTicker:
    def test_delegates_to_okx(self, service, sample_crypto_ticker):
        service.okx.get_ticker = MagicMock(return_value=sample_crypto_ticker)
        result = service.get_ticker("BTC")
        service.okx.get_ticker.assert_called_once_with("BTC")
        assert result["symbol"] == "BTC-USDT"


class TestGetKlines:
    def test_delegates_to_okx_with_defaults(self, service, sample_crypto_klines):
        service.okx.fetch_klines = MagicMock(return_value=sample_crypto_klines)
        result = service.get_klines("ETH", "SPOT", "1m", 1716854400, 1716854460)
        service.okx.fetch_klines.assert_called_once_with(
            "ETH", "SPOT", "1m", 1716854400, 1716854460, 1000
        )
        assert len(result) == 2

    def test_passes_custom_limit(self, service):
        service.okx.fetch_klines = MagicMock(return_value=[])
        service.get_klines("ETH", "SPOT", "5m", 1716854400, 1716854460, limit=500)
        service.okx.fetch_klines.assert_called_once_with(
            "ETH", "SPOT", "5m", 1716854400, 1716854460, 500
        )


class TestGetMa:
    def test_delegates_to_okx_with_defaults(self, service, sample_crypto_ma):
        service.okx.get_ma = MagicMock(return_value=sample_crypto_ma)
        result = service.get_ma("BTC")
        service.okx.get_ma.assert_called_once_with(
            "BTC", "SPOT", "1m", None, 0, 0, 500
        )
        assert result["symbol"] == "BTC-USDT"

    def test_passes_custom_params(self, service):
        service.okx.get_ma = MagicMock(return_value={})
        service.get_ma("BTC", "SPOT", "1H", [5, 10, 20], 1716854400, 1716940800, 100)
        service.okx.get_ma.assert_called_once_with(
            "BTC", "SPOT", "1H", [5, 10, 20], 1716854400, 1716940800, 100
        )
