from daos.transaction_dao import TransactionDao
from apis.market_client import MarketClient


class HoldingService:
    def __init__(self):
        self.dao = TransactionDao()
        self.market = MarketClient()

    def get_holdings(self, asset_type: str = None,
                     page: int = 1, page_size: int = 20) -> dict:
        rows = self.dao.get_all_for_holding()
        if not rows:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        # Group by (asset_type, asset_code)
        groups = {}
        for r in rows:
            key = (r["asset_type"], r["asset_code"])
            if key not in groups:
                groups[key] = {
                    "asset_type": r["asset_type"],
                    "asset_code": r["asset_code"],
                    "asset_name": r["asset_name"],
                    "portfolio_tags": set(),
                    "transactions": [],
                }
            groups[key]["transactions"].append(r)
            if r.get("portfolio_tag"):
                groups[key]["portfolio_tags"].add(r["portfolio_tag"])

        result = []
        for (a_type, a_code), g in groups.items():
            total_qty = 0.0
            total_cost = 0.0

            for t in g["transactions"]:
                if t["trans_type"] == "buy":
                    total_qty += float(t["quantity"])
                    total_cost += float(t["quantity"]) * float(t["price"]) + float(t["fee"] or 0)
                elif t["trans_type"] == "sell":
                    sell_qty = float(t["quantity"])
                    if total_qty > 0:
                        # 按平均成本法等比例扣减成本
                        avg_cost_before_sell = total_cost / total_qty
                        total_cost -= avg_cost_before_sell * sell_qty
                    total_qty -= sell_qty

            if total_qty <= 0:
                continue

            avg_cost = total_cost / total_qty

            if asset_type and a_type != asset_type:
                continue

            holding = {
                "asset_type": a_type,
                "asset_code": a_code,
                "asset_name": g["asset_name"],
                "total_quantity": round(total_qty, 4),
                "avg_cost": round(avg_cost, 4),
                "total_cost": round(total_cost, 2),
                "portfolio_tags": list(g["portfolio_tags"]),
                "current_price": None,
                "market_value": None,
                "unrealized_pnl": None,
                "unrealized_pnl_pct": None,
            }

            # Enrich with real-time price
            price_info = self.market.get_realtime_price(a_type, a_code)
            if price_info and price_info.get("current_price") is not None:
                cp = float(price_info["current_price"])
                holding["current_price"] = cp
                holding["market_value"] = round(total_qty * cp, 2)
                holding["unrealized_pnl"] = round(total_qty * cp - total_cost, 2)
                if total_cost > 0:
                    holding["unrealized_pnl_pct"] = round(
                        (total_qty * cp - total_cost) / total_cost * 100, 2
                    )
                holding.update({k: v for k, v in price_info.items() if k != "current_price"})

            result.append(holding)

        total = len(result)
        offset = (page - 1) * page_size
        return {
            "items": result[offset:offset + page_size],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_holding_detail(self, asset_type: str, asset_code: str) -> dict | None:
        holdings = self.get_holdings(asset_type, page=1, page_size=999999)
        for h in holdings["items"]:
            if h["asset_code"] == asset_code:
                # Attach individual transaction records
                rows = self.dao.list_by_user(asset_type=asset_type, asset_code=asset_code)
                h["transactions"] = [dict(r) for r in rows]
                # Compute per-batch P&L
                current_price = h.get("current_price")
                for t in h["transactions"]:
                    if t["trans_type"] == "buy" and current_price is not None:
                        qty = float(t["quantity"])
                        cost = float(t["price"])
                        t["batch_pnl_pct"] = round(
                            (float(current_price) - cost) / cost * 100, 2
                        )
                        t["batch_pnl"] = round((float(current_price) - cost) * qty, 2)
                return h
        return None

    def create_holding(self, asset_type: str, asset_code: str,
                       asset_name: str, trans_type: str, price: float,
                       quantity: float, fee: float, trans_date: str,
                       portfolio_tag: str = None, notes: str = None) -> int:
        return self.dao.create(
            asset_type=asset_type,
            asset_code=asset_code,
            asset_name=asset_name,
            trans_type=trans_type,
            price=price,
            quantity=quantity,
            fee=fee,
            trans_date=trans_date,
            portfolio_tag=portfolio_tag,
            notes=notes,
        )

    def delete_holding(self, asset_type: str = None,
                       asset_code: str = None, trans_id: int = None) -> int:
        if trans_id is not None:
            return 1 if self.dao.delete(trans_id) else 0
        if asset_type and asset_code:
            return self.dao.delete_by_asset(asset_type, asset_code)
        return 0
