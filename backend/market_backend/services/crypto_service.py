from apis.okx_api import OkxApi


class CryptoService:
    def __init__(self):
        self.okx = OkxApi()

    def get_books(self, symbol: str):
        return self.okx.get_books(symbol)

    def get_ticker(self, symbol: str):
        return self.okx.get_ticker(symbol)

    def get_klines(self, symbol: str, market_type: str, interval: str,
                   start_time: int, end_time: int, limit: int = 1000):
        return self.okx.fetch_klines(symbol, market_type, interval,
                                     start_time, end_time, limit)

    def get_ma(self, symbol: str, market_type: str = "SPOT", interval: str = "1m",
               ma_periods=None, start_time: int = 0, end_time: int = 0, limit: int = 500):
        return self.okx.get_ma(symbol, market_type, interval,
                               ma_periods, start_time, end_time, limit)
