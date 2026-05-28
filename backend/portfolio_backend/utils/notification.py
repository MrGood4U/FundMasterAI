import logging

logger = logging.getLogger(__name__)


def send_phone_alert(phone: str, alert_info: dict) -> bool:
    logger.info(
        "[FAKE PHONE CALL] To: %s | Asset: %s %s | Alert: %s | Current price: %s",
        phone,
        alert_info.get("asset_type"),
        alert_info.get("asset_code"),
        alert_info.get("alert_type"),
        alert_info.get("current_price"),
    )
    return True


def send_email_alert(email: str, alert_info: dict) -> bool:
    logger.info(
        "[FAKE EMAIL] To: %s | Asset: %s %s | Alert: %s | Current price: %s",
        email,
        alert_info.get("asset_type"),
        alert_info.get("asset_code"),
        alert_info.get("alert_type"),
        alert_info.get("current_price"),
    )
    return True
