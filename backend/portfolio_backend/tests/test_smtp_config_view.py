"""
SMTP 配置接口测试 — 直接触及数据库，不 mock Service/DAO 层。

前置条件：
  - MySQL 可用（否则全部 skip）
  - smtp_config 表存在，且 id=1 行已由 app 启动逻辑 ensure_exists() 保证存在
"""

import json

import pytest

from daos.smtp_config_dao import SmtpConfigDao


def _db_available():
    """检测数据库是否可达。"""
    try:
        from daos.base_dao import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False


@pytest.fixture
def save_and_restore():
    """保存并恢复 id=0 的 SMTP 配置，保证测试隔离。"""
    dao = SmtpConfigDao()
    original = dao.get()
    yield
    # 恢复原始配置
    if original:
        dao.update(
            email=original.get("email"),
            sender_name=original.get("sender_name"),
            smtp_host=original.get("smtp_host"),
            smtp_port=original.get("smtp_port"),
            password=original.get("password"),
            encryption=original.get("encryption"),
        )


class TestGetSmtpConfig:
    """测试 GET /api/portfolio/smtp_config — 读取 SMTP 配置"""

    @pytest.mark.skipif(not _db_available(), reason="MySQL not available")
    def test_get_config_success(self, client, save_and_restore):
        """正常读取 SMTP 配置，应返回 id=0 的记录且密码脱敏。"""
        resp = client.get("/api/portfolio/smtp_config/get_config")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.data}"

        data = json.loads(resp.data)
        assert data["code"] == 200
        assert data["data"] is not None

        cfg = data["data"]
        # id 始终为 1（MySQL AUTO_INCREMENT 不接受 0）
        assert cfg["id"] == 1, f"Expected id=1, got {cfg['id']}"
        # 密码必须脱敏
        assert cfg["password"] == "******", f"Password not masked: {cfg['password']}"
        # 核心字段应存在
        for field in ("email", "smtp_host", "smtp_port", "encryption"):
            assert field in cfg, f"Missing field: {field}"


class TestUpdateSmtpConfig:
    """测试 POST /api/portfolio/smtp_config/update — 更新 SMTP 配置"""

    @pytest.mark.skipif(not _db_available(), reason="MySQL not available")
    def test_update_success(self, client, save_and_restore):
        """更新 SMTP 配置后，再读取验证更新已持久化到数据库。"""
        # 1) 更新配置
        update_payload = {
            "email": "test@fundmaster.ai",
            "sender_name": "TestSender",
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "password": "test_password_123",
            "encryption": "tls",
        }
        resp = client.post(
            "/api/portfolio/smtp_config/update_config",
            data=json.dumps(update_payload),
            content_type="application/json",
        )
        assert resp.status_code == 200, f"Update failed: {resp.status_code} {resp.data}"
        update_data = json.loads(resp.data)
        assert update_data["code"] == 200

        # 2) 读取配置，验证数据库中的值已变更
        resp2 = client.get("/api/portfolio/smtp_config/get_config")
        assert resp2.status_code == 200
        cfg = json.loads(resp2.data)["data"]

        assert cfg["email"] == "test@fundmaster.ai"
        assert cfg["sender_name"] == "TestSender"
        assert cfg["smtp_host"] == "smtp.test.com"
        assert cfg["smtp_port"] == 587
        assert cfg["encryption"] == "tls"
        # 密码应脱敏（读取时不返回明文）
        assert cfg["password"] == "******"

        # 3) 直接从 DAO 验证数据库中的明文密码
        dao = SmtpConfigDao()
        row = dao.get()
        assert row is not None
        assert row["password"] == "test_password_123"

    @pytest.mark.skipif(not _db_available(), reason="MySQL not available")
    def test_update_empty_body(self, client):
        """空请求体应返回 400。"""
        resp = client.post(
            "/api/portfolio/smtp_config/update_config",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
