from datetime import datetime
import akshare as ak

class AksharePublicFund:
    def eastmoney_real_time(self, symbol: str):
        if symbol == "ETF":
            return ak.fund_etf_spot_em()
        elif symbol == "LOF":
            return ak.fund_lof_spot_em()
        return None


    def eastmoney_hist_min(self, symbol: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        adjusts = ['', 'qfq', 'hfq'] # 不复权、前复权、后复权
        if adjust not in adjusts:
            return None
        
        periods = ['1', '5', '15', '30', '60'] # 1分钟、5分钟、15分钟、30分钟、60分钟
        if period not in periods:
            return None
        
        symbols = ['ETF', 'LOF']
        if symbol not in symbols:
            return None

        if symbol == "ETF":
            return ak.fund_etf_hist_min_em(symbol=code, period=period, adjust=adjust, start_date=start_date, end_date=end_date)
        elif symbol == "LOF":
            return ak.fund_lof_hist_min_em(symbol=code, period=period, adjust=adjust, start_date=start_date, end_date=end_date)
        else:
            return None


    def eastmoney_hist(self, symbol: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        adjusts = ['', 'qfq', 'hfq'] # 不复权、前复权、后复权
        if adjust not in adjusts:
            return None
        
        periods = ['daily', 'weekly', 'monthly'] # 日线、周线、月线
        if period not in periods:
            return None
        
        symbols = ['ETF', 'LOF']
        if symbol not in symbols:
            return None

        if symbol == "ETF":
            return ak.fund_etf_hist_em(symbol=code, period=period, adjust=adjust, start_date=start_date, end_date=end_date)
        elif symbol == "LOF":
            return ak.fund_lof_hist_em(symbol=code, period=period, adjust=adjust, start_date=start_date, end_date=end_date)
        else:
            return None


    def sina_hist(self, code: str, start_date: str, end_date: str):
        result = fund_etf_hist_sina_df = ak.fund_etf_hist_sina(symbol=code)
        mask = (result["date"] >= pd.to_datetime(start_date)) & (result["date"] <= pd.to_datetime(end_date))
        result = result.loc[mask]
        return result
        
    
    def tonghuashun_real_time(self, symbol: str):
        tonghuashun_symbol = ["股票型", "债券型", "混合型", "ETF", "LOF", "QDII", "保本型", "指数型", ""]
        if symbol not in tonghuashun_symbol:
            return None
        today = datetime.now().strftime("%Y%m%d")
        return ak.fund_etf_category_ths(symbol=symbol, date=today)

    
    def sina_real_time(self, symbol: str):
        sina_symbol = ["封闭式基金", "ETF基金", "LOF基金"]
        if symbol not in sina_symbol:
            return None
        return ak.fund_etf_spot_sina(symbol=symbol)


    def real_time(self, symbol: str, platform: str):
        if platform == "eastmoney":
            return self.eastmoney_real_time(symbol)
        elif platform == "tonghuashun":
            return self.tonghuashun_real_time(symbol)
        elif platform == "sina":
            return self.sina_real_time(symbol)
        else:
            return None


    def hist_min(self, symbol: str, platform: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        if platform == "eastmoney":
            return self.eastmoney_hist_min(symbol, code, start_date, end_date, period, adjust)
        else:
            return None


    def hist(self, symbol: str, platform: str, code: str, start_date: str, end_date: str, period: str, adjust: str):
        if platform == "eastmoney":
            return self.eastmoney_hist(symbol, code, start_date, end_date, period, adjust)
        elif platform == 'sina':
            return self.sina_hist(symbol, code, start_date, end_date, period, adjust)
        else:
            return None