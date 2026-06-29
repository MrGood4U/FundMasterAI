from daos.base_dao import get_connection


class AlertDao:

    def create(self, asset_type: str, asset_code: str,
               alert_type: str, trigger_mode: str, trigger_price: float = None,
               trigger_pct: float = None, reference_trans_id: int = None,
               notify_phone: bool = False, notify_email: bool = False,
               notes: str = None) -> int:
        sql = """
            INSERT INTO price_alert
                (asset_type, asset_code, alert_type, trigger_mode,
                 trigger_price, trigger_pct, reference_trans_id,
                 notify_phone, notify_email, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (asset_type, asset_code, alert_type,
                                  trigger_mode, trigger_price, trigger_pct,
                                  reference_trans_id, notify_phone, notify_email,
                                  notes))
                conn.commit()
                return cur.lastrowid

    def get_by_id(self, alert_id: int) -> dict | None:
        sql = "SELECT * FROM price_alert WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (alert_id,))
                return cur.fetchone()

    def update(self, alert_id: int, **kwargs) -> bool:
        allowed = {"alert_type", "trigger_mode", "trigger_price", "trigger_pct",
                   "reference_trans_id", "notify_phone", "notify_email",
                   "is_enabled", "notes"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return False
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values()) + [alert_id]
        sql = f"UPDATE price_alert SET {set_clause} WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
                conn.commit()
                return cur.rowcount > 0

    def delete(self, alert_id: int) -> bool:
        sql = "DELETE FROM price_alert WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (alert_id,))
                conn.commit()
                return cur.rowcount > 0

    def count_by_user(self, is_enabled: bool = None,
                      asset_type: str = None) -> int:
        conditions = []
        params = []
        if is_enabled is not None:
            conditions.append("is_enabled = %s")
            params.append(1 if is_enabled else 0)
        if asset_type:
            conditions.append("asset_type = %s")
            params.append(asset_type)

        if conditions:
            where = " AND ".join(conditions)
            sql = f"SELECT COUNT(*) FROM price_alert WHERE {where}"
        else:
            sql = "SELECT COUNT(*) FROM price_alert"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return row["COUNT(*)"] if row else 0

    def list_by_user(self, is_enabled: bool = None,
                     asset_type: str = None,
                     limit: int = None, offset: int = None) -> list:
        conditions = []
        params = []

        if is_enabled is not None:
            conditions.append("is_enabled = %s")
            params.append(1 if is_enabled else 0)
        if asset_type:
            conditions.append("asset_type = %s")
            params.append(asset_type)

        if conditions:
            where = " AND ".join(conditions)
            sql = f"SELECT * FROM price_alert WHERE {where} ORDER BY created_at DESC"
        else:
            sql = "SELECT * FROM price_alert ORDER BY created_at DESC"

        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            sql += " OFFSET %s"
            params.append(offset)

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def mark_notified(self, alert_id: int) -> bool:
        sql = "UPDATE price_alert SET notified_at = NOW() WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (alert_id,))
                conn.commit()
                return cur.rowcount > 0
