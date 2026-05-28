import pytest
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.fixture
def okx_api():
    with patch("apis.okx_api.config") as mock_config:
        mock_config.get_okx_api_key.return_value = "test_key"
        mock_config.get_okx_api_secret.return_value = "test_secret"
        mock_config.get_okx_api_pass.return_value = "test_pass"

        with patch("apis.okx_api.Account"), patch("apis.okx_api.OkxSPOT"):
            from apis.okx_api import OkxApi

            api = OkxApi()
            api.spot_market = MagicMock()
            yield api


class TestPresetSymbol:
    def test_known_symbol_maps(self, okx_api):
        assert okx_api.preset_symbol("BTC") == "BTC-USDT"
        assert okx_api.preset_symbol("BTC_USDT") == "BTC-USDT"
        assert okx_api.preset_symbol("ETH") == "ETH-USDT"
        assert okx_api.preset_symbol("SOL") == "SOL-USDT"

    def test_unknown_symbol_passes_through(self, okx_api):
        assert okx_api.preset_symbol("RANDOM-COIN") == "RANDOM-COIN"

    def test_empty_string_passes_through(self, okx_api):
        assert okx_api.preset_symbol("") == ""


class TestGetBooks:
    def test_parses_bids_and_asks(self, okx_api):
        okx_api.spot_market.get_books.return_value = {
            "data": {
                "bids": [["96500.5", "0.5"], ["96490.0", "2.0"]],
                "asks": [["96550.0", "0.8"], ["96560.0", "1.5"]],
            }
        }
        result = okx_api.get_books("BTC")
        assert len(result["bids"]) == 2
        assert result["bids"][0] == [96500.5, 0.5]
        assert result["bids"][1] == [96490.0, 2.0]
        assert len(result["asks"]) == 2
        assert result["asks"][0] == [96550.0, 0.8]
        assert result["asks"][1] == [96560.0, 1.5]

    def test_presets_symbol_before_call(self, okx_api):
        okx_api.spot_market.get_books.return_value = {
            "data": {"bids": [], "asks": []}
        }
        okx_api.get_books("BTC")
        okx_api.spot_market.get_books.assert_called_once_with(instId="BTC-USDT")


class TestGetTicker:
    def test_parses_ticker_fields(self, okx_api):
        okx_api.spot_market.get_ticker.return_value = {
            "data": {
                "last": "96520.5",
                "high24h": "97500.0",
                "low24h": "95800.0",
                "vol24h": "15000.5",
                "open24h": "96000.0",
            }
        }
        result = okx_api.get_ticker("BTC")
        assert result["symbol"] == "BTC-USDT"
        assert result["last_price"] == 96520.5
        assert result["high24h"] == 97500.0
        assert result["low24h"] == 95800.0
        assert result["volume24h"] == 15000.5
        assert "change_percent" in result

    def test_change_percent_calculation(self, okx_api):
        okx_api.spot_market.get_ticker.return_value = {
            "data": {
                "last": "110.0",
                "high24h": "115.0",
                "low24h": "95.0",
                "vol24h": "1000.0",
                "open24h": "100.0",
            }
        }
        result = okx_api.get_ticker("SOL")
        assert result["change_percent"] == pytest.approx(0.10)


class TestFetchKlines:
    def test_returns_structured_list(self, okx_api):
        okx_api.spot_market.get_history_candle.return_value = {
            "data": [
                {"ts": 1716854400000, "o": "96500.0", "h": "96600.0",
                 "l": "96400.0", "c": "96550.0", "vol": "100.5", "volCcy": "9700000.0"},
            ]
        }
        okx_api.spot_market.candle_to_df.return_value = MagicMock()
        mock_df = MagicMock()
        mock_df.to_json.return_value = '[{"ts":1716854400000,"o":96500.0,"h":96600.0,"l":96400.0,"c":96550.0,"vol":100.5,"volCcy":9700000.0}]'
        okx_api.spot_market.candle_to_df.return_value = mock_df

        result = okx_api.fetch_klines("ETH", "SPOT", "1m", 1716854400, 1716854460)

        assert len(result) == 1
        assert result[0]["start_time"] == 1716854400000
        assert result[0]["open_price"] == 96500.0
        assert result[0]["close_price"] == 96550.0
        assert result[0]["volume"] == 100.5
        assert result[0]["volume_currency"] == "9700000.0"


class TestGetMa:
    def test_falls_back_to_default_periods(self, okx_api):
        okx_api.spot_market.get_history_candle.return_value = {"data": []}
        okx_api.spot_market.candle_to_df.return_value = MagicMock()
        mock_df = MagicMock()
        mock_df.empty = True
        okx_api.spot_market.candle_to_df.return_value = mock_df

        result = okx_api.get_ma("BTC", start_time=1716854400, end_time=1716940800)
        assert result == []

    def test_accepts_string_ma_periods(self, okx_api):
        import time

        now = int(time.time())
        end = now
        start = end - 86400

        okx_api.spot_market.get_history_candle.return_value = {"data": []}
        okx_api.spot_market.candle_to_df.return_value = MagicMock()
        mock_df = MagicMock()
        mock_df.empty = True
        okx_api.spot_market.candle_to_df.return_value = mock_df

        result = okx_api.get_ma("BTC", start_time=start, end_time=end, ma_periods="5,10,20")
        assert result == []
