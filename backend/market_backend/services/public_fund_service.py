from daos.market_dao import MarketDao
from apis.akshare_public_fund_api import AksharePublicFund
from utils.kline_generator import KLineGenerator
from apis.efinance_api import EfinanceAPI
import pandas as pd

class PublicFundService:
    def __init__(self):
        self.dao = MarketDao()
        self.efapi = EfinanceAPI()
        self.akapi = AksharePublicFund()

    def get_one_real_time(self, name: str, code: str, platform: str, symbol: str): 
        df = self.akapi.real_time(symbol, platform)
        data = df.to_dict(orient="records")
        if df is None or df.empty:
            return [], f"no data found for platform: {platform} , symbol: {symbol}"
        df_size = len(data)
        if code is not None:
            get_one_result = [item for item in data if ("code" in item and item["code"] == code) or ("fund_code" in item and item["fund_code"] == code)]
        elif name is not None:
            get_one_result = [item for item in data if ("name" in item and item["name"] == name) or ("fund_name" in item and item["fund_name"] == name)]
        result_size = len(get_one_result)

        if df_size > 0 and result_size == 0:
            return [], f"no match found for code: {code} or name: {name} in platform: {platform} , symbol: {symbol}"
        return get_one_result, None
    
    def get_all_real_time(self, platform: str = None, symbol: str = None):
        df = self.akapi.real_time(symbol, platform)
        if df is None or df.empty:
            return []
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    def get_hist(self, symbol: str, platform: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        df = self.efapi.hist(code)
        if df is None or df.empty:
            return []
        if start_date:
            df["date"] = pd.to_datetime(df["date"])
            mask = (df["date"] >= pd.to_datetime(start_date))
            df = df.loc[mask]
        if end_date:
            df["date"] = pd.to_datetime(df["date"])
            mask = (df["date"] <= pd.to_datetime(end_date))
            df = df.loc[mask]
        if df.empty:
            return []
        return df.to_dict(orient="records")
    
    def get_hist_min(self, symbol:str, platform: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        df = self.akapi.hist_min(symbol, platform, code, start_date, end_date, period, adjust)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_hist_kline(self, symbol: str, platform: str, code: str,
                       start_date: str, end_date: str, period: str, adjust: str):
        df = self.efapi.hist(code)
        if df is None or df.empty:
            return []
        if start_date and end_date:
            df["date"] = pd.to_datetime(df["date"])
            mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
            df = df.loc[mask]
        if df.empty:
            return []
        gen = KLineGenerator(df, "unit_net_value")
        return gen.all().to_dict(orient="records")

    def get_hist_min_kline(self, symbol: str, platform: str, code: str,
                           start_date: str, end_date: str, period: str, adjust: str):
        df = self.akapi.hist_min(symbol, platform, code, start_date, end_date, period, adjust)
        if df is None or df.empty:
            return []
        gen = KLineGenerator(df)
        return gen.all().to_dict(orient="records")
    
    def get_fund_name_list(self):
        df = self.akapi.get_fund_name_list()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_portfolio_holds(self, code: str, year: str):
        df = self.akapi.get_fund_portfolio_holds(code, year)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_individual_analysis(self, code: str):
        df = self.akapi.get_fund_individual_analysis(code)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_individual_profit_probability(self, code: str):
        df = self.akapi.get_fund_individual_profit_probability(code)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_value_estimation(self, code: str, fund_type: str):
        df = self.akapi.get_fund_value_estimation_list(fund_type)
        if df is None or df.empty:
            return []
        data = df.to_dict(orient="records")
        if code is not None:
            get_one_result = [item for item in data if ("code" in item and item["code"] == code) or ("fund_code" in item and item["fund_code"] == code)]
        return get_one_result
    
    def get_fund_value_estimation_list(self, fund_type: str):
        df = self.akapi.get_fund_value_estimation_list(fund_type)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def fund_open_fund_rank(self, fund_type: str):
        df = self.akapi.fund_open_fund_rank(fund_type)
        if df is None or df.empty:
            return []
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    def get_fund_info_index(self, symbol: str, indicator: str):
        df = self.akapi.get_fund_info_index(symbol, indicator)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_individual_basic_info(self, code: str):
        df = self.akapi.get_fund_individual_basic_info(code)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_individual_detail_hold(self, code: str, date: str):
        df = self.akapi.get_fund_individual_detail_hold(code, date)
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")

    def get_fund_portfolio_industry_allocation_em(self, code: str, year: str):
        result = self.akapi.get_fund_portfolio_industry_allocation_em(code, year)
        if isinstance(result, list) or result is None or result.empty:
            return []
        return result.to_dict(orient="records")

    def get_fund_portfolio_hold_stock(self, code: str, year: str):
        result = self.akapi.get_fund_portfolio_hold_stock(code, year)
        if isinstance(result, list) or result is None or result.empty:
            return []
        return result.to_dict(orient="records")

    def get_fund_portfolio_hold_bond(self, code: str, year: str):
        result = self.akapi.get_fund_portfolio_hold_bond(code, year)
        if isinstance(result, list) or result is None or result.empty:
            return []
        return result.to_dict(orient="records")