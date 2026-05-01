from daos.market_dao import MarketDao
from apis.akshare_public_fund_api import AksharePublicFund
import pandas as pd

class PublicFundService:
    def __init__(self):
        self.dao = MarketDao()
        self.akapi = AksharePublicFund()

    def get_one_real_time(self, name: str, code: str, platform: str, symbol: str):
        df = self.akapi.real_time(symbol, platform)
        data = df.to_dict(orient="records")
        if code is not None:
            get_one_result = [item for item in data if ("代码" in item and item["代码"] == code) or ("基金代码" in item and item["基金代码"] == code)]
        elif name is not None:
            get_one_result = [item for item in data if ("名称" in item and item["名称"] == name) or ("基金名称" in item and item["基金名称"] == name)]
        return get_one_result
    
    def get_all_real_time(self, platform: str = None, symbol: str = None):
        df = self.akapi.real_time(symbol, platform)
        return df.to_dict(orient="records")

    def get_hist(self, symbol: str, platform: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        df = self.akapi.hist(symbol, platform, code, start_date, end_date, period, adjust)
        return df.to_dict(orient="records")
    
    def get_hist_min(self, symbol: str, platform: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        df = self.akapi.hist_min(symbol, platform, code, start_date, end_date, period, adjust)
        return df.to_dict(orient="records")