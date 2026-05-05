from datetime import datetime
import akshare as ak

class AkshareNews:
    def stock_news_recent(self, symbol: str):
        df = ak.stock_news_em(symbol=symbol)
        return df

    def public_fund_announcement(self, code: str):
        df = ak.fund_announcement_em(symbol=code)
        return df