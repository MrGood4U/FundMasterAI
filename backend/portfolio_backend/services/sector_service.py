"""行业暴露服务：穿透基金持仓 + 关键词行业识别。"""

from collections import defaultdict

from services.holding_service import HoldingService
from apis.market_client import MarketClient
from utils.industry_keywords import classify_stock


class SectorService:
    def __init__(self):
        self.holding_svc = HoldingService()
        self.market = MarketClient()

    # ------------------------------------------------------------------
    # 行业暴露分布
    # ------------------------------------------------------------------

    def get_sector_exposure(self) -> dict:
        """穿透汇总持仓的行业市值分布。

        流程：
        1. 拉取用户全部持仓
        2. 直接持有的个股 → 关键词归入行业
        3. 持有的基金 → 调 market_backend 获取基金持仓股票 → 按比例分摊到行业
        4. 债券/加密货币暂不参与行业分类（直接跳过）
        """
        holdings = self.holding_svc.get_holdings(page=1, page_size=999999)
        items = holdings.get("items", [])

        # sector → total market value
        sector_mv: dict[str, float] = defaultdict(float)
        # stock_code → {name, market_value} 用于集中度分析
        stock_exposure: dict[str, dict] = {}
        total_mv = 0.0

        for h in items:
            at = h.get("asset_type")
            code = h.get("asset_code", "")
            name = h.get("asset_name", "")
            mv = float(h.get("market_value") or 0)

            if at == "stock":
                # 直接持股 → 关键词分类
                sector = classify_stock(name)
                sector_mv[sector] += mv
                total_mv += mv
                if code not in stock_exposure:
                    stock_exposure[code] = {"name": name, "market_value": 0.0}
                stock_exposure[code]["market_value"] += mv

            elif at == "fund":
                # 基金 → 穿透持仓
                self._penetrate_fund(code, name, mv, sector_mv, stock_exposure)
                total_mv += mv

            elif at == "bond":
                sector_mv["债券"] += mv
                total_mv += mv

            elif at == "crypto":
                sector_mv["加密货币"] += mv
                total_mv += mv

        # Build sorted result
        sector_list = []
        for sector, mv in sorted(sector_mv.items(), key=lambda x: x[1], reverse=True):
            pct = round(mv / total_mv * 100, 2) if total_mv > 0 else 0.0
            sector_list.append({
                "sector": sector,
                "market_value": round(mv, 2),
                "pct": pct,
            })

        return {
            "items": sector_list,
            "total_market_value": round(total_mv, 2),
        }

    # ------------------------------------------------------------------
    # 集中度分析
    # ------------------------------------------------------------------

    def get_sector_concentration(self) -> dict:
        """集中度分析：Top3 行业占比、Top5 个股占比、风险标记。"""
        exposure = self.get_sector_exposure()
        sectors = exposure.get("items", [])
        total_mv = exposure.get("total_market_value", 0)

        # Top 3 行业占比
        top3_sectors = sectors[:3]
        top3_pct = round(sum(s["pct"] for s in top3_sectors), 2)

        # 个股集中度 —— rebuild stock_exposure from holdings
        holdings = self.holding_svc.get_holdings(page=1, page_size=999999)
        stock_mv: dict[str, dict] = {}
        for h in holdings.get("items", []):
            at = h.get("asset_type")
            code = h.get("asset_code", "")
            name = h.get("asset_name", "")
            mv = float(h.get("market_value") or 0)

            if at == "stock":
                key = f"{code}|{name}"
                if key not in stock_mv:
                    stock_mv[key] = {"code": code, "name": name, "market_value": 0.0}
                stock_mv[key]["market_value"] += mv

        top5_stocks = sorted(
            stock_mv.values(), key=lambda x: x["market_value"], reverse=True
        )[:5]
        for s in top5_stocks:
            s["pct"] = round(s["market_value"] / total_mv * 100, 2) if total_mv > 0 else 0.0

        top5_pct = round(sum(s["pct"] for s in top5_stocks), 2)

        # 风险标记
        warnings = []
        if top3_pct > 70:
            warnings.append(f"前3大行业占比 {top3_pct}%，集中度过高")
        if top5_pct > 50:
            warnings.append(f"前5大个股占比 {top5_pct}%，个股集中风险较高")
        for s in top5_stocks[:3]:
            if s["pct"] > 20:
                warnings.append(f"{s['name']}({s['code']}) 单一个股占比 {s['pct']}%，超过20%")

        return {
            "top3_sectors": top3_sectors,
            "top3_sectors_pct": top3_pct,
            "top5_stocks": top5_stocks,
            "top5_stocks_pct": top5_pct,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # 内部：穿透单只基金
    # ------------------------------------------------------------------

    def _penetrate_fund(self, fund_code: str, fund_name: str, fund_mv: float,
                        sector_mv: dict, stock_exposure: dict):
        """穿透单只基金，将基金市值按持仓比例分摊到各行业和个股。"""
        holds = self.market.get_fund_portfolio_holds(fund_code)
        if not holds:
            # 无持仓数据时，按基金名称做关键词归类作为 fallback
            sector = classify_stock(fund_name)
            sector_mv[sector] += fund_mv
            return

        # 计算每只持仓股占基金净值的比例总和（用于归一化）
        total_pct = 0.0
        parsed = []
        for row in holds:
            try:
                pct = float(row.get("net_value_pct") or 0)
            except (TypeError, ValueError):
                pct = 0.0
            total_pct += pct
            parsed.append({
                "stock_code": row.get("stock_code", ""),
                "stock_name": row.get("stock_name", ""),
                "net_value_pct": pct,
            })

        if total_pct <= 0:
            # 退化：按基金名称归入行业
            sector = classify_stock(fund_name)
            sector_mv[sector] += fund_mv
            return

        # 按持仓权重分摊基金市值
        for item in parsed:
            weight = item["net_value_pct"] / total_pct
            stock_mv = fund_mv * weight

            sector = classify_stock(item["stock_name"])
            sector_mv[sector] += stock_mv

            code = item["stock_code"]
            if code not in stock_exposure:
                stock_exposure[code] = {"name": item["stock_name"], "market_value": 0.0}
            stock_exposure[code]["market_value"] += stock_mv
