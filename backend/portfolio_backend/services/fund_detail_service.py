from apis.market_client import MarketClient


class FundDetailService:
    """基金明细查询服务：代理 market_backend 的基金持仓/行业/资产配置接口。"""

    def __init__(self):
        self.client = MarketClient()

    def get_detail_hold(self, code: str, date: str = None) -> list | None:
        """资产配置：股票/债券/现金等各类资产占净值比例。"""
        return self.client.get_fund_detail_hold(code, date)

    def get_industry_allocation(self, code: str, year: str = None) -> list | None:
        """行业配置：基金在各行业的持仓分布。"""
        return self.client.get_fund_industry_allocation(code, year)

    def get_stock_holds(self, code: str, year: str = None) -> list | None:
        """股票持仓：基金持有的全部股票明细。"""
        return self.client.get_fund_stock_holds(code, year)

    def get_bond_holds(self, code: str, year: str = None) -> list | None:
        """债券持仓：基金持有的全部债券明细。"""
        return self.client.get_fund_bond_holds(code, year)
