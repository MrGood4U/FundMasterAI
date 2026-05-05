from daos.example_dao import ExampleDao
from apis.akshare_news_api import AkshareNews


class NewsService:
    def __init__(self):
        self.dao = ExampleDao()
        self.news_api = AkshareNews()
    
    def get_stock_recent_news(self, symbol: str):
        df = self.news_api.stock_news_recent(symbol)
        return df.to_dict(orient="records")

    def get_public_fund_announcement(self, code: str):
        df = self.news_api.public_fund_announcement(code)
        return df.to_dict(orient="records")
