from daos.market_dao import MarketDao
from apis.akshare_stock_api import AkshareStock
import pandas as pd

class StockService:
    def __init__(self):
        self.dao = MarketDao()
        self.akapi = AkshareStock()

    def get_all_a_spot(self, platform: str):
        df = self.akapi.a_spot_all(platform)
        return df.to_dict(orient="records")

    def get_a_spot(self, platform: str, code: str, name:str):
        df = self.akapi.a_spot_one(platform, code, name)
        return df.to_dict(orient="records")

    def get_a_hist(self, platform: str, code: str, period: str, start_date: str, end_date: str, adjust: str):
        df = self.akapi.a_hist(platform, code, period, start_date, end_date, adjust)
        return df.to_dict(orient="records")

    def get_a_bid_ask(self, platform: str, code: str):
        df = self.akapi.a_bid_ask(platform, code)
        return df.to_dict(orient="records")