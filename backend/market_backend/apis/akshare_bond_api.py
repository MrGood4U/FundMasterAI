from datetime import datetime
from datetime import timedelta
import akshare as ak
import re

from apis.field_mapping import (
    apply_mapping,
    BOND_SPOT_QUOTE_MAP,
    BOND_SPOT_DEAL_MAP,
    BOND_INFO_SEARCH_MAP,
    BOND_CHINA_YIELD_MAP,
)

class AkshareBond:
    def is_ymd_format(self, s: str) -> bool:
        pattern = r"^\d{8}$"
        return bool(re.fullmatch(pattern, s))

    def bond_spot_quote(self):
        df = ak.bond_spot_quote()
        return apply_mapping(df, BOND_SPOT_QUOTE_MAP)

    def bond_spot_deal(self):
        df = ak.bond_spot_deal()
        return apply_mapping(df, BOND_SPOT_DEAL_MAP)

    def bond_spot_quote_search_by_bond_name(self, bond_name: str):
        df = self.bond_spot_quote()
        return df[df["bond_name"] == bond_name]

    def bond_spot_quote_search_by_bond_code(self, bond_code: str):
        bond_name = self.bond_get_name_by_code(bond_code)
        if bond_name is None:
            return None
        df = self.bond_spot_quote()
        return df[df["bond_name"] == bond_name]

    def bond_spot_deal_search_by_bond_name(self, bond_name: str):
        df = self.bond_spot_deal()
        return df[df["bond_name"] == bond_name]

    def bond_spot_deal_search_by_bond_code(self, bond_code: str):
        bond_name = self.bond_get_name_by_code(bond_code)
        if bond_name is None:
            return None
        df = self.bond_spot_deal()
        return df[df["bond_name"] == bond_name]

    def bond_info_search(self, bond_name: str, bond_code: str, bond_issue: str, bond_type: str, coupon_type: str, issue_year: str, grade: str, underwriter: str):
        df = ak.bond_info_cm(bond_name=bond_name, bond_code=bond_code, bond_issue=bond_issue, bond_type=bond_type, coupon_type=coupon_type, issue_year=issue_year, grade=grade, underwriter=underwriter)
        return apply_mapping(df, BOND_INFO_SEARCH_MAP)

    def bond_get_name_by_code(self, bond_code: str):
        df = self.bond_info_search(bond_name="", bond_code=bond_code, bond_issue="", bond_type="", coupon_type="", issue_year="", grade="", underwriter="")
        if df is not None and len(df) > 0:
            return df.iloc[0]["bond_name"]
        else:
            return None

    def bond_china_yield_all(self, start_date: str, end_date: str):
        # start_date and end_date format: "YYYYMMDD"
        # start_date to end_date should not exceed 1 year, otherwise it will return empty data
        if self.is_ymd_format(start_date) is False or self.is_ymd_format(end_date) is False:
            return None, "Invalid date format. Please use YYYYMMDD."
        if datetime.strptime(end_date, "%Y%m%d") < datetime.strptime(start_date, "%Y%m%d"):
            return None, "end_date should be greater than or equal to start_date"
        if datetime.strptime(end_date, "%Y%m%d") - datetime.strptime(start_date, "%Y%m%d") > timedelta(days=365):
            return None, "start_date to end_date should not exceed 1 year"
        df = ak.bond_china_yield(start_date=start_date, end_date=end_date)
        return apply_mapping(df, BOND_CHINA_YIELD_MAP)

    def bond_china_yield_search_by_curve_name(self, curve_name: str, start_date: str, end_date: str):
        df, msg = self.bond_china_yield_all(start_date, end_date)
        if msg is not None:
            return None, msg
        return df[df["curve_name"].str.contains(curve_name)], None