from daos.watchlist_dao import WatchlistDao
from apis.market_client import MarketClient


class WatchlistService:
    def __init__(self):
        self.dao = WatchlistDao()
        self.market = MarketClient()

    def add(self, **kwargs) -> dict:
        required = ["asset_type", "asset_code"]
        for field in required:
            if field not in kwargs or kwargs[field] is None:
                return {"error": f"{field} is required"}

        if kwargs["asset_type"] not in ("stock", "fund", "bond", "crypto"):
            return {"error": "asset_type must be stock, fund, bond, or crypto"}

        watch_id = self.dao.add(
            asset_type=kwargs["asset_type"],
            asset_code=kwargs["asset_code"],
            asset_name=kwargs.get("asset_name"),
            target_price=float(kwargs["target_price"]) if kwargs.get("target_price") is not None else None,
            priority=int(kwargs.get("priority", 0)),
            notes=kwargs.get("notes"),
        )
        return {"id": watch_id}

    def remove(self, watchlist_id: int) -> bool:
        return self.dao.remove(watchlist_id)

    def list_by_user(self, asset_type: str = None,
                     page: int = 1, page_size: int = 20) -> dict:
        total = self.dao.count_by_user(asset_type)
        offset = (page - 1) * page_size
        rows = self.dao.list_by_user(asset_type, limit=page_size, offset=offset)
        items = []
        for r in rows:
            item = dict(r)
            price_info = self.market.get_realtime_price(r["asset_type"], r["asset_code"])
            if price_info:
                item["price_info"] = price_info
            items.append(item)
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
