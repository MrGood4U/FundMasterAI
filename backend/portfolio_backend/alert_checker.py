import logging
import threading
import time

from daos.alert_dao import AlertDao
from daos.transaction_dao import TransactionDao
from daos.user_profile_dao import UserProfileDao
from apis.market_client import MarketClient
from utils.notification import send_phone_alert, send_email_alert

logger = logging.getLogger(__name__)


class AlertChecker:

    def __init__(self):
        self.alert_dao = AlertDao()
        self.trans_dao = TransactionDao()
        self.profile_dao = UserProfileDao()
        self.market = MarketClient()

    def _get_cost_basis(self, alert: dict) -> float | None:
        ref_trans_id = alert.get("reference_trans_id")
        if ref_trans_id:
            trans = self.trans_dao.get_by_id(ref_trans_id)
            if trans:
                return float(trans["price"])
            return None

        rows = self.trans_dao.list_by_user(
            asset_type=alert["asset_type"],
            asset_code=alert["asset_code"],
        )
        total_cost = 0.0
        total_qty = 0.0
        for t in rows:
            if t["trans_type"] == "buy":
                qty = float(t["quantity"])
                total_qty += qty
                total_cost += qty * float(t["price"]) + float(t.get("fee") or 0)

        if total_qty <= 0:
            return None
        return total_cost / total_qty

    def _is_triggered(self, alert: dict, current_price: float) -> bool:
        trigger_mode = alert["trigger_mode"]
        alert_type = alert["alert_type"]

        if trigger_mode == "price":
            threshold = float(alert["trigger_price"])
            if alert_type in ("price_above", "stop_profit"):
                return current_price >= threshold
            else:
                return current_price <= threshold

        # pct mode
        cost_basis = self._get_cost_basis(alert)
        if cost_basis is None:
            return False

        change_pct = (current_price - cost_basis) / cost_basis
        threshold = float(alert["trigger_pct"])

        if alert_type in ("price_above", "stop_profit"):
            return change_pct >= threshold
        else:
            return change_pct <= threshold

    def check_and_notify(self):
        alerts = self.alert_dao.list_by_user(is_enabled=True)
        if not alerts:
            return

        profile = self.profile_dao.get()
        phone = profile.get("phone") if profile else None
        email = profile.get("email") if profile else None

        for alert in alerts:
            try:
                alert = dict(alert)
                price_info = self.market.get_realtime_price(
                    alert["asset_type"], alert["asset_code"]
                )
                if not price_info or price_info.get("current_price") is None:
                    continue

                current_price = float(price_info["current_price"])

                if not self._is_triggered(alert, current_price):
                    continue

                alert["current_price"] = current_price
                logger.info(
                    "Alert #%s triggered: %s %s %s at price %s",
                    alert["id"], alert["asset_type"], alert["asset_code"],
                    alert["alert_type"], current_price,
                )

                if alert.get("notify_phone") and phone:
                    send_phone_alert(phone, alert)
                if alert.get("notify_email") and email:
                    send_email_alert(email, alert)

                self.alert_dao.update(alert["id"], is_enabled=0)
                self.alert_dao.mark_notified(alert["id"])
            except Exception:
                logger.exception(
                    "Failed to process alert #%s", alert.get("id")
                )


def start_alert_checker(app):
    interval = app.config.get("ALERT_CHECK_INTERVAL_MINUTES", 5)
    interval_seconds = interval * 60

    checker = AlertChecker()

    def _loop():
        logger.info(
            "Alert checker started, checking every %d minute(s)", interval
        )
        while True:
            try:
                checker.check_and_notify()
            except Exception:
                logger.exception("Alert checker cycle failed")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
