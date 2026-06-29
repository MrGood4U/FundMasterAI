from datetime import datetime
import akshare as ak

from apis.field_mapping import (
    apply_mapping,
    FUND_ANNOUNCEMENT_FIELDS,
    STOCK_NEWS_EM_FIELDS
)

class AkshareNews:
    def stock_news_recent(self, symbol: str):
        df = ak.stock_news_em(symbol=symbol)
        return apply_mapping(df, STOCK_NEWS_EM_FIELDS)

    def public_fund_announcement(self, code: str):
        df = ak.fund_announcement_dividend_em(symbol=code)
        if not df.empty:
            df['url'] = "https://fund.eastmoney.com/gonggao/" + df['基金代码'] + "," + df['报告ID'] + ".html"
        return apply_mapping(df, FUND_ANNOUNCEMENT_FIELDS)