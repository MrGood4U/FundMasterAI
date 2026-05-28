from daos.alert_dao import AlertDao
from daos.user_profile_dao import UserProfileDao


class AlertService:
    def __init__(self):
        self.dao = AlertDao()
        self.profile_dao = UserProfileDao()

    def create(self, **kwargs) -> dict:
        required = ["asset_type", "asset_code", "alert_type", "trigger_mode"]
        for field in required:
            if field not in kwargs or kwargs[field] is None:
                return {"error": f"{field} is required"}

        if kwargs["alert_type"] not in ("stop_profit", "stop_loss", "price_above", "price_below"):
            return {"error": "invalid alert_type"}

        if kwargs["trigger_mode"] not in ("price", "pct"):
            return {"error": "trigger_mode must be price or pct"}

        if kwargs["asset_type"] not in ("stock", "fund", "crypto"):
            return {"error": "asset_type must be stock, fund, or crypto"}

        # Validate trigger values
        trigger_mode = kwargs["trigger_mode"]
        trigger_price = kwargs.get("trigger_price")
        trigger_pct = kwargs.get("trigger_pct")

        if trigger_mode == "price" and trigger_price is None:
            return {"error": "trigger_price is required when trigger_mode is price"}
        if trigger_mode == "pct" and trigger_pct is None:
            return {"error": "trigger_pct is required when trigger_mode is pct"}

        # Validate notification channels
        notify_phone = bool(kwargs.get("notify_phone", False))
        notify_email = bool(kwargs.get("notify_email", False))

        if notify_phone or notify_email:
            profile = self.profile_dao.get()
            if notify_phone and (not profile or not profile.get("phone") or not profile.get("phone_verified")):
                return {"error": "phone is not set or not verified"}
            if notify_email and (not profile or not profile.get("email") or not profile.get("email_verified")):
                return {"error": "email is not set or not verified"}

        alert_id = self.dao.create(
            asset_type=kwargs["asset_type"],
            asset_code=kwargs["asset_code"],
            alert_type=kwargs["alert_type"],
            trigger_mode=trigger_mode,
            trigger_price=float(trigger_price) if trigger_price is not None else None,
            trigger_pct=float(trigger_pct) if trigger_pct is not None else None,
            reference_trans_id=kwargs.get("reference_trans_id"),
            notify_phone=notify_phone,
            notify_email=notify_email,
            notes=kwargs.get("notes"),
        )
        return {"id": alert_id}

    def get_by_id(self, alert_id: int) -> dict:
        row = self.dao.get_by_id(alert_id)
        if row is None:
            return {}
        return dict(row)

    def update(self, alert_id: int, **kwargs) -> bool:
        return self.dao.update(alert_id, **kwargs)

    def delete(self, alert_id: int) -> bool:
        return self.dao.delete(alert_id)

    def list_by_user(self, is_enabled: bool = None,
                     asset_type: str = None,
                     page: int = 1, page_size: int = 20) -> dict:
        total = self.dao.count_by_user(is_enabled, asset_type)
        offset = (page - 1) * page_size
        rows = self.dao.list_by_user(is_enabled, asset_type,
                                     limit=page_size, offset=offset)
        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def mark_notified(self, alert_id: int) -> bool:
        return self.dao.mark_notified(alert_id)
