from daos.smtp_config_dao import SmtpConfigDao
from utils.notification import send_test_email


class SmtpConfigService:
    """单用户系统的 SMTP 配置 Service — 始终操作 id=1 这一条记录。"""

    def __init__(self):
        self.dao = SmtpConfigDao()

    def get_config(self) -> dict:
        """获取唯一的 SMTP 配置。"""
        row = self.dao.get()
        if row is None:
            return {}
        return dict(row)

    def update(self, **kwargs) -> bool:
        """更新 SMTP 配置。"""
        if "email" in kwargs and kwargs["email"] is not None:
            email = kwargs["email"].strip()
            if "@" not in email:
                return False
            kwargs["email"] = email
        if "encryption" in kwargs and kwargs["encryption"] is not None:
            if kwargs["encryption"] not in ("tls", "ssl", "none"):
                return False
        if "smtp_port" in kwargs and kwargs["smtp_port"] is not None:
            port = int(kwargs["smtp_port"])
            if port <= 0 or port > 65535:
                return False
            kwargs["smtp_port"] = port
        return self.dao.update(**kwargs)

    def test_email(self, to_email: str) -> dict:
        """使用当前配置发送测试邮件。"""
        config = self.dao.get()
        if not config:
            return {"error": "smtp config not found, please configure first"}
        success = send_test_email(to_email, smtp_config=config)
        if success:
            return {"message": "test email sent successfully"}
        return {"error": "failed to send test email, check server logs for details"}
