from datetime import datetime
import akshare as ak

class AkshareStock:
    def eastmoney_a_spot_one(self, code: str, name: str):
        df = ak.stock_zh_a_spot_em()
        if code != None and code != "":
            return df[df["代码"] == code]
        elif name != None and name != "":
            return df[df["名称"] == name]
        else:
            return None


    def eastmoney_a_spot_one(self):
        df = ak.stock_zh_a_spot_em()
        return df
    
    
    def eastmoney_a_hist(self, code: str, period: str, start_date: str, end_date: str, adjust: str):
        periods = ['daily', 'weekly', 'monthly'] # 日线、周线、月线
        if period not in periods:
            return None
        adjusts = ['qfq', 'hfq']
        if adjust not in adjusts:
            adjust = ""
        df = ak.stock_zh_a_hist(symbol = code, period = period, start_date = start_date, end_date = end_date, adjust = adjust)
        return df

    def sina_a_hist(self, code: str, period: str, start_date: str, end_date: str, adjust: str):
        adjusts = ['qfq', 'hfq', 'qfq-factor', 'hfq-factor']
        if adjust not in adjusts:
            adjust = ""
        df = ak.stock_zh_a_daily(symbol = code, start_date = start_date, end_date = end_date, adjust = adjust)
        return df


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