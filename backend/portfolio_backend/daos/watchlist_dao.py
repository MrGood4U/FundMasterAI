from daos.base_dao import get_connection


class WatchlistDao:

    def add(self, asset_type: str, asset_code: str,
            asset_name: str = None, target_price: float = None,
            priority: int = 0, notes: str = None) -> int:
        sql = """
            INSERT INTO watchlist (asset_type, asset_code, asset_name,
                                   target_price, priority, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                asset_name = COALESCE(VALUES(asset_name), asset_name),
                target_price = COALESCE(VALUES(target_price), target_price),
                priority = VALUES(priority),
                notes = COALESCE(VALUES(notes), notes)
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (asset_type, asset_code, asset_name,
                                  target_price, priority, notes))
                conn.commit()
                return cur.lastrowid

    def remove(self, watchlist_id: int) -> bool:
        sql = "DELETE FROM watchlist WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (watchlist_id,))
                conn.commit()
                return cur.rowcount > 0

    def count_by_user(self, asset_type: str = None) -> int:
        conditions = []
        params = []
        if asset_type:
            conditions.append("asset_type = %s")
            params.append(asset_type)
        if conditions:
            where = " AND ".join(conditions)
            sql = f"SELECT COUNT(*) FROM watchlist WHERE {where}"
        else:
            sql = "SELECT COUNT(*) FROM watchlist"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return row["COUNT(*)"] if row else 0

    def list_by_user(self, asset_type: str = None,
                     limit: int = None, offset: int = None) -> list:
        conditions = []
        params = []
        if asset_type:
            conditions.append("asset_type = %s")
            params.append(asset_type)
        if conditions:
            where = " AND ".join(conditions)
            sql = f"SELECT * FROM watchlist WHERE {where} ORDER BY priority DESC, created_at DESC"
        else:
            sql = "SELECT * FROM watchlist ORDER BY priority DESC, created_at DESC"

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

    def get_by_asset(self, asset_type: str, asset_code: str) -> dict | None:
        sql = "SELECT * FROM watchlist WHERE asset_type = %s AND asset_code = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (asset_type, asset_code))
                return cur.fetchone()
