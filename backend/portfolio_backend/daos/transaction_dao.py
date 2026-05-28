from daos.base_dao import get_connection


class TransactionDao:

    def create(self, asset_type: str, asset_code: str,
               asset_name: str, trans_type: str, price: float, quantity: float,
               fee: float, trans_date: str, portfolio_tag: str = None,
               notes: str = None) -> int:
        sql = """
            INSERT INTO transactions
                (asset_type, asset_code, asset_name, trans_type,
                 price, quantity, fee, trans_date, portfolio_tag, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (asset_type, asset_code, asset_name,
                                  trans_type, price, quantity, fee, trans_date,
                                  portfolio_tag, notes))
                conn.commit()
                return cur.lastrowid

    def get_by_id(self, trans_id: int) -> dict | None:
        sql = "SELECT * FROM transactions WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trans_id,))
                return cur.fetchone()

    def update(self, trans_id: int, **kwargs) -> bool:
        allowed = {"asset_name", "price", "quantity", "fee", "trans_date",
                   "portfolio_tag", "notes"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return False
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values()) + [trans_id]
        sql = f"UPDATE transactions SET {set_clause} WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
                conn.commit()
                return cur.rowcount > 0

    def delete(self, trans_id: int) -> bool:
        sql = "DELETE FROM transactions WHERE id = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trans_id,))
                conn.commit()
                return cur.rowcount > 0

    def count_by_user(self, asset_type: str = None,
                      asset_code: str = None, trans_type: str = None,
                      start_date: str = None, end_date: str = None) -> int:
        conditions = []
        params = []
        if asset_type:
            conditions.append("asset_type = %s")
            params.append(asset_type)
        if asset_code:
            conditions.append("asset_code = %s")
            params.append(asset_code)
        if trans_type:
            conditions.append("trans_type = %s")
            params.append(trans_type)
        if start_date:
            conditions.append("trans_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("trans_date <= %s")
            params.append(end_date)

        if conditions:
            where = " AND ".join(conditions)
            sql = f"SELECT COUNT(*) FROM transactions WHERE {where}"
        else:
            sql = "SELECT COUNT(*) FROM transactions"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return row["COUNT(*)"] if row else 0

    def list_by_user(self, asset_type: str = None,
                     asset_code: str = None, trans_type: str = None,
                     start_date: str = None, end_date: str = None,
                     limit: int = None, offset: int = None) -> list:
        conditions = []
        params = []

        if asset_type:
            conditions.append("asset_type = %s")
            params.append(asset_type)
        if asset_code:
            conditions.append("asset_code = %s")
            params.append(asset_code)
        if trans_type:
            conditions.append("trans_type = %s")
            params.append(trans_type)
        if start_date:
            conditions.append("trans_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("trans_date <= %s")
            params.append(end_date)

        if conditions:
            where = " AND ".join(conditions)
            sql = f"SELECT * FROM transactions WHERE {where} ORDER BY trans_date DESC, id DESC"
        else:
            sql = "SELECT * FROM transactions ORDER BY trans_date DESC, id DESC"

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

    def get_all_for_holding(self) -> list:
        sql = "SELECT * FROM transactions ORDER BY trans_date ASC, id ASC"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()
