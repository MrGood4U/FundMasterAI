from daos.transaction_dao import TransactionDao


class TransactionService:
    def __init__(self):
        self.dao = TransactionDao()

    def create(self, **kwargs) -> dict:
        required = ["asset_type", "asset_code", "trans_type", "price", "quantity", "trans_date"]
        for field in required:
            if field not in kwargs or kwargs[field] is None:
                return {"error": f"{field} is required"}

        if kwargs["trans_type"] not in ("buy", "sell"):
            return {"error": "trans_type must be buy or sell"}

        if kwargs["asset_type"] not in ("stock", "fund", "crypto"):
            return {"error": "asset_type must be stock, fund, or crypto"}

        trans_id = self.dao.create(
            asset_type=kwargs["asset_type"],
            asset_code=kwargs["asset_code"],
            asset_name=kwargs.get("asset_name"),
            trans_type=kwargs["trans_type"],
            price=float(kwargs["price"]),
            quantity=float(kwargs["quantity"]),
            fee=float(kwargs.get("fee", 0)),
            trans_date=kwargs["trans_date"],
            portfolio_tag=kwargs.get("portfolio_tag"),
            notes=kwargs.get("notes"),
        )
        return {"id": trans_id}

    def get_by_id(self, trans_id: int) -> dict:
        row = self.dao.get_by_id(trans_id)
        if row is None:
            return {}
        return dict(row)

    def update(self, trans_id: int, **kwargs) -> bool:
        return self.dao.update(trans_id, **kwargs)

    def delete(self, trans_id: int) -> bool:
        return self.dao.delete(trans_id)

    def list_by_user(self, asset_type: str = None,
                     asset_code: str = None, trans_type: str = None,
                     start_date: str = None, end_date: str = None,
                     page: int = 1, page_size: int = 20) -> dict:
        total = self.dao.count_by_user(asset_type, asset_code,
                                       trans_type, start_date, end_date)
        offset = (page - 1) * page_size
        rows = self.dao.list_by_user(asset_type, asset_code,
                                     trans_type, start_date, end_date,
                                     limit=page_size, offset=offset)
        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
