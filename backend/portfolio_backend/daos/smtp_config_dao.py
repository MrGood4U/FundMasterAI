from daos.base_dao import get_connection


class SmtpConfigDao:
    """单用户系统的 SMTP 配置 DAO — 只维护 id=0 这一条记录。"""

    CONFIG_ID = 1

    def ensure_exists(self) -> None:
        """确保 id=1 的那条 SMTP 配置行存在（不存在则插入占位行）。"""
        sql = """
            INSERT IGNORE INTO smtp_config
                (id, email, smtp_host, smtp_port, password, encryption)
            VALUES (%s, '', '', 587, '', 'tls')
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (self.CONFIG_ID,))
                conn.commit()

    def get(self) -> dict | None:
        """获取 id=1 的 SMTP 配置。"""
        sql = "SELECT * FROM smtp_config WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (self.CONFIG_ID,))
                return cur.fetchone()

    def update(self, **kwargs) -> bool:
        """更新 id=1 的 SMTP 配置。只更新传入的非 None 字段。"""
        allowed = {"email", "sender_name", "smtp_host", "smtp_port",
                   "password", "encryption"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return False

        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values()) + [self.CONFIG_ID]

        sql = f"UPDATE smtp_config SET {set_clause} WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
                conn.commit()
                return cur.rowcount > 0
