from datetime import datetime
import akshare as ak

from apis.field_mapping import (
    apply_mapping,
    STOCK_SPOT_EM_MAP,
    STOCK_HIST_EM_MAP,
    BID_ASK_EM_MAP,
    STOCK_HIST_SINA_MAP,
)

class AkshareStock:
    def eastmoney_a_spot_one(self, code: str, name: str):
        df = apply_mapping(ak.stock_zh_a_spot_em(), STOCK_SPOT_EM_MAP)
        if code is not None and code != "":
            return df[df["code"] == code]
        elif name is not None and name != "":
            return df[df["name"] == name]
        else:
            return None

    def eastmoney_a_spot_all(self):
        df = ak.stock_zh_a_spot_em()
        return apply_mapping(df, STOCK_SPOT_EM_MAP)

    def eastmoney_a_hist(self, code: str, period: str, start_date: str, end_date: str, adjust: str):
        periods = ['daily', 'weekly', 'monthly']
        if period not in periods:
            return None
        adjusts = ['qfq', 'hfq']
        if adjust not in adjusts:
            adjust = ""
        df = ak.stock_zh_a_hist(symbol=code, period=period, start_date=start_date, end_date=end_date, adjust=adjust)
        return apply_mapping(df, STOCK_HIST_EM_MAP)

    def eastmoney_a_bid_ask(self, code: str):
        df = ak.stock_bid_ask_em(symbol=code)
        df_pivot = df.pivot_table(values="value", columns="item").reset_index(drop=True)
        return apply_mapping(df_pivot, BID_ASK_EM_MAP)

    def sina_a_hist(self, code: str, period: str, start_date: str, end_date: str, adjust: str):
        adjusts = ['qfq', 'hfq', 'qfq-factor', 'hfq-factor']
        if adjust not in adjusts:
            adjust = ""
        df = ak.stock_zh_a_daily(symbol=code, start_date=start_date, end_date=end_date, adjust=adjust)
        return apply_mapping(df, STOCK_HIST_SINA_MAP)

    def a_spot_one(self, platform: str, code: str, name: str):
        if platform == "eastmoney":
            return self.eastmoney_a_spot_one(code, name)
        else:
            return None

    def a_spot_all(self, platform: str):
        if platform == "eastmoney":
            return self.eastmoney_a_spot_all()
        else:
            return None

    def a_hist(self, platform: str, code: str, period: str, start_date: str, end_date: str, adjust: str):
        if platform == "eastmoney":
            return self.eastmoney_a_hist(code, period, start_date, end_date, adjust)
        elif platform == "sina":
            return self.sina_a_hist(code, period, start_date, end_date, adjust)
        else:
            return None

    def a_bid_ask(self, platform: str, code: str):
        if platform == "eastmoney":
            return self.eastmoney_a_bid_ask(code)
        else:
            return None