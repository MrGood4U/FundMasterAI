from daos.market_dao import MarketDao
from apis.akshare_bond_api import AkshareBond
from utils.kline_generator import KLineGenerator
import pandas as pd


class BondService:
    def __init__(self):
        self.dao = MarketDao()
        self.akapi = AkshareBond()

    def get_bond_spot_quote(self):
        df = self.akapi.bond_spot_quote()
        if df is None or df.empty:
            return []
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    def get_bond_spot_deal(self):
        df = self.akapi.bond_spot_deal()
        if df is None or df.empty:
            return []
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    def get_bond_spot_quote_search(self, bond_name: str = None, bond_code: str = None):
        if bond_code is not None:
            df = self.akapi.bond_spot_quote_search_by_bond_code(bond_code)
        elif bond_name is not None:
            df = self.akapi.bond_spot_quote_search_by_bond_name(bond_name)
        else:
            return []
        if df is None or df.empty:
            return []
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    def get_bond_spot_deal_search(self, bond_name: str = None, bond_code: str = None):
        if bond_code is not None:
            df = self.akapi.bond_spot_deal_search_by_bond_code(bond_code)
        elif bond_name is not None:
            df = self.akapi.bond_spot_deal_search_by_bond_name(bond_name)
        else:
            return []
        if df is None or df.empty:
            return []
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    def get_bond_info_search(self, bond_name: str = "", bond_code: str = "",
                              bond_issue: str = "", bond_type: str = "",
                              coupon_type: str = "", issue_year: str = "",
                              grade: str = "", underwriter: str = ""):
        df = self.akapi.bond_info_search(
            bond_name=bond_name, bond_code=bond_code, bond_issue=bond_issue,
            bond_type=bond_type, coupon_type=coupon_type, issue_year=issue_year,
            grade=grade, underwriter=underwriter,
        )
        if df is None or df.empty:
            return []
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    def get_bond_china_yield_all(self, start_date: str, end_date: str):
        df, msg = self.akapi.bond_china_yield_all(start_date, end_date)
        if msg is not None:
            return [], msg
        if df is None or df.empty:
            return []
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    def get_bond_china_yield_search(self, curve_name: str, start_date: str, end_date: str):
        df, msg = self.akapi.bond_china_yield_search_by_curve_name(curve_name, start_date, end_date)
        if msg is not None:
            return [], msg
        if df is None or df.empty:
            return []
        df = df.where(pd.notna(df), None)
        return df.to_dict(orient="records")

    def get_bond_name_by_code(self, bond_code: str):
        name = self.akapi.bond_get_name_by_code(bond_code)
        return name
