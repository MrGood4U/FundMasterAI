import requests
from config import Config


class MarketClient:

    def __init__(self):
        self.base_url = Config.MARKET_BACKEND_URL.rstrip("/")

    def _post(self, path: str, body: dict) -> dict | list | None:
        try:
            resp = requests.post(
                f"{self.base_url}{path}",
                json=body,
                timeout=5,
            )
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data")
            return None
        except Exception:
            return None

    def get_realtime_price(self, asset_type: str, asset_code: str) -> dict | None:
        if asset_type == "stock":
            return self._get_stock_price(asset_code)
        elif asset_type == "fund":
            return self._get_fund_price(asset_code)
        elif asset_type == "bond":
            return self._get_bond_price(asset_code)
        elif asset_type == "crypto":
            return self._get_crypto_price(asset_code)
        return None

    def _get_stock_price(self, code: str) -> dict | None:
        data = self._post("/api/market/stock/a/one_spot", {
            "platform": "eastmoney",
            "code": code,
            "name": None,
        })
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            return {
                "current_price": item.get("latest_price"),
                "change_pct": item.get("change_pct"),
                "change_amount": item.get("change_amount"),
                "high": item.get("high"),
                "low": item.get("low"),
                "open": item.get("open"),
                "prev_close": item.get("prev_close"),
            }
        return None

    def _get_fund_price(self, code: str) -> dict | None:
        data = self._post("/api/market/fund_public/real_time_get_one", {
            "platform": "tonghuashun",
            "symbol": "all",
            "code": code,
            "name": None,
        })
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            return {
                "current_price": item.get("current_unit_net_value"),
                "change_pct": item.get("growth_rate"),
                "change_amount": item.get("growth_value"),
                "prev_close": item.get("prev_unit_net_value"),
                "fund_name": item.get("fund_name"),
                "fund_type": item.get("fund_type"),
            }
        return None

    def _get_bond_price(self, code: str) -> dict | None:
        data = self._post("/api/market/bond/spot_quote_search", {
            "bond_code": code,
        })
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            return {
                "current_price": item.get("buying_clean_price"),
                "buying_clean_price": item.get("buying_clean_price"),
                "selling_clean_price": item.get("selling_clean_price"),
                "buying_yield": item.get("buying_yield"),
                "selling_yield": item.get("selling_yield"),
                "quote_institution": item.get("quote_institution"),
            }
        return None

    def _get_crypto_price(self, symbol: str) -> dict | None:
        data = self._post("/api/market/crypto/ticker", {
            "symbol": symbol,
        })
        if data and isinstance(data, dict):
            return {
                "current_price": data.get("last"),
                "change_pct": data.get("change_pct"),
                "high": data.get("high_24h"),
                "low": data.get("low_24h"),
                "volume": data.get("vol_24h"),
            }
        return None

    def get_fund_portfolio_holds(self, fund_code: str, year: str = None) -> list:
        """获取基金持仓股票明细。"""
        from datetime import datetime
        body = {"code": fund_code}
        if year:
            body["year"] = year
        else:
            body["year"] = str(datetime.now().year)
        data = self._post("/api/market/fund_public/portfolio_holds", body)
        if data and isinstance(data, list):
            return data
        return []

    def get_fund_detail_hold(self, code: str, date: str = None) -> list | None:
        """获取基金资产配置明细（股票/债券/现金等各类资产占净值比例）。

        返回 list[{"asset_type": str, "pct": float}]，如:
          [{"asset_type": "股票", "pct": 72.35}, {"asset_type": "债券", "pct": 18.20}]
        """
        from datetime import datetime
        body = {
            "code": code,
            "date": date or datetime.now().strftime("%Y%m%d"),
        }
        return self._post("/api/market/fund_public/individual_detail_hold", body)

    def get_fund_industry_allocation(self, code: str, year: str = None) -> list | None:
        """获取基金行业配置，返回最新报告期的行业持仓分布。

        返回 list[{"sequence": int, "industry_category": str, "pct": float,
                  "market_value": float, "as_of_date": str}]
        """
        from datetime import datetime
        body = {
            "code": code,
            "year": year or str(datetime.now().year),
        }
        return self._post("/api/market/fund_public/portfolio_industry_allocation", body)

    def get_fund_stock_holds(self, code: str, year: str = None) -> list | None:
        """获取基金股票持仓明细，返回最新报告期的全部股票持仓。

        返回 list[{"sequence": int, "stock_code": str, "stock_name": str, "pct": float,
                  "hold_shares": float, "hold_market_value": float, "quarter": str}]
        """
        from datetime import datetime
        body = {
            "code": code,
            "year": year or str(datetime.now().year),
        }
        return self._post("/api/market/fund_public/portfolio_hold_stock", body)

    def get_fund_bond_holds(self, code: str, year: str = None) -> list | None:
        """获取基金债券持仓明细，返回最新报告期的全部债券持仓。

        返回 list[{"sequence": int, "bond_code": str, "bond_name": str, "pct": float,
                  "hold_market_value": float, "quarter": str}]
        """
        from datetime import datetime
        body = {
            "code": code,
            "year": year or str(datetime.now().year),
        }
        return self._post("/api/market/fund_public/portfolio_hold_bond", body)
