import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict | None:
    """从数据库获取 SMTP 配置（单用户系统，始终取 id=0 的记录）。"""
    try:
        from daos.smtp_config_dao import SmtpConfigDao
        dao = SmtpConfigDao()
        return dao.get()
    except Exception:
        logger.exception("Failed to load SMTP config from database")
        return None


def _build_email_body(alert_info: dict) -> str:
    """构建邮件正文"""
    asset_type = alert_info.get("asset_type", "")
    asset_code = alert_info.get("asset_code", "")
    alert_type = alert_info.get("alert_type", "")
    current_price = alert_info.get("current_price", "N/A")
    trigger_price = alert_info.get("trigger_price", "N/A")
    trigger_pct = alert_info.get("trigger_pct", "N/A")
    trigger_mode = alert_info.get("trigger_mode", "")

    if alert_type == "stop_profit":
        alert_type_cn = "止盈提醒"
    elif alert_type == "stop_loss":
        alert_type_cn = "止损提醒"
    elif alert_type == "price_above":
        alert_type_cn = "价格上涨提醒"
    elif alert_type == "price_below":
        alert_type_cn = "价格下跌提醒"
    else:
        alert_type_cn = alert_type

    if trigger_mode == "price":
        threshold_desc = f"触发价格: {trigger_price}"
    elif trigger_mode == "pct":
        threshold_desc = f"触发百分比: {trigger_pct * 100:.2f}%" if trigger_pct else "触发百分比: N/A"
    else:
        threshold_desc = ""

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #333;">FundMasterAI 价格预警</h2>
        <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
            <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">资产类型</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{asset_type}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">资产代码</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{asset_code}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">预警类型</td>
                <td style="padding: 8px; border: 1px solid #ddd; color: #e74c3c; font-weight: bold;">{alert_type_cn}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">当前价格</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{current_price}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">{threshold_desc.split(':')[0] if ':' in threshold_desc else '触发条件'}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{threshold_desc.split(':', 1)[1].strip() if ':' in threshold_desc else threshold_desc}</td></tr>
        </table>
        <p style="color: #999; margin-top: 20px; font-size: 12px;">
            此邮件由 FundMasterAI 系统自动发送于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </body>
    </html>
    """
    return body


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
    """发送邮件预警通知"""
    config = _get_smtp_config()
    if not config:
        logger.warning("[EMAIL] No SMTP config found, falling back to fake email")
        logger.info(
            "[FAKE EMAIL] To: %s | Asset: %s %s | Alert: %s | Current price: %s",
            email,
            alert_info.get("asset_type"),
            alert_info.get("asset_code"),
            alert_info.get("alert_type"),
            alert_info.get("current_price"),
        )
        return True

    try:
        msg = MIMEMultipart("alternative")
        sender_name = config.get("sender_name") or config["email"]
        msg["From"] = f"{sender_name} <{config['email']}>"
        msg["To"] = email
        msg["Subject"] = (
            f"[FundMasterAI] {alert_info.get('asset_code', '')} "
            f"{alert_info.get('alert_type', '预警')} | "
            f"当前价格 {alert_info.get('current_price', 'N/A')}"
        )
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")

        html_body = _build_email_body(alert_info)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        encryption = config.get("encryption", "tls")
        smtp_host = config["smtp_host"]
        smtp_port = config["smtp_port"]
        smtp_user = config["email"]
        smtp_password = config["password"]

        if encryption == "ssl":
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            if encryption == "tls":
                server.starttls()

        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email, msg.as_string())
        server.quit()

        logger.info(
            "[EMAIL SENT] To: %s | Subject: %s",
            email, msg["Subject"],
        )
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "[EMAIL FAILED] SMTP authentication error for %s@%s:%s — "
            "请检查邮箱密码/应用专用密码是否正确",
            config["email"], config["smtp_host"], config["smtp_port"],
        )
        return False
    except smtplib.SMTPConnectError:
        logger.error(
            "[EMAIL FAILED] Cannot connect to SMTP server %s:%s",
            config["smtp_host"], config["smtp_port"],
        )
        return False
    except Exception:
        logger.exception("[EMAIL FAILED] Unexpected error sending email")
        return False


def send_test_email(to_email: str, smtp_config: dict = None) -> bool:
    """发送测试邮件，用于验证 SMTP 配置是否正确

    Args:
        to_email: 收件人邮箱
        smtp_config: 可选，直接传入 SMTP 配置字典（包含 email, smtp_host,
                     smtp_port, password, encryption）。不传则从数据库读取默认配置。

    Returns:
        是否发送成功
    """
    config = smtp_config or _get_smtp_config()
    if not config:
        logger.error("[TEST EMAIL] No SMTP config available")
        return False

    try:
        msg = MIMEMultipart("alternative")
        sender_name = config.get("sender_name") or config["email"]
        msg["From"] = f"{sender_name} <{config['email']}>"
        msg["To"] = to_email
        msg["Subject"] = "[FundMasterAI] SMTP 配置测试邮件"
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800")

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #27ae60;">SMTP 配置测试成功</h2>
            <p>恭喜！您的 FundMasterAI SMTP 邮件服务配置正确。</p>
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">发件邮箱</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{config['email']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">SMTP 服务器</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{config['smtp_host']}:{config['smtp_port']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd; background: #f5f5f5;">加密方式</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{config.get('encryption', 'tls')}</td></tr>
            </table>
            <p style="color: #999; margin-top: 20px; font-size: 12px;">
                此邮件由 FundMasterAI 系统自动发送于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        encryption = config.get("encryption", "tls")
        if encryption == "ssl":
            server = smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"], timeout=15)
        else:
            server = smtplib.SMTP(config["smtp_host"], config["smtp_port"], timeout=15)
            if encryption == "tls":
                server.starttls()

        server.login(config["email"], config["password"])
        server.sendmail(config["email"], to_email, msg.as_string())
        server.quit()

        logger.info("[TEST EMAIL SENT] To: %s", to_email)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("[TEST EMAIL FAILED] SMTP authentication error — 请检查邮箱密码/应用专用密码")
        return False
    except smtplib.SMTPConnectError:
        logger.error("[TEST EMAIL FAILED] Cannot connect to SMTP server")
        return False
    except Exception:
        logger.exception("[TEST EMAIL FAILED] Unexpected error")
        return False
