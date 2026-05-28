from daos.base_dao import get_connection


class UserProfileDao:

    def get(self) -> dict | None:
        sql = "SELECT * FROM user_profile LIMIT 1"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchone()

    def upsert(self, phone: str = None, email: str = None) -> int:
        sql = """
            INSERT INTO user_profile (id, phone, email)
            VALUES (1, %s, %s)
            ON DUPLICATE KEY UPDATE
                phone = COALESCE(VALUES(phone), phone),
                email = COALESCE(VALUES(email), email)
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (phone, email))
                conn.commit()
                return cur.lastrowid

    def update_phone(self, phone: str) -> bool:
        sql = "UPDATE user_profile SET phone = %s, phone_verified = 0 WHERE id = 1"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (phone,))
                conn.commit()
                return cur.rowcount > 0

    def update_email(self, email: str) -> bool:
        sql = "UPDATE user_profile SET email = %s, email_verified = 0 WHERE id = 1"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (email,))
                conn.commit()
                return cur.rowcount > 0

    def set_phone_verified(self) -> bool:
        sql = "UPDATE user_profile SET phone_verified = 1 WHERE id = 1"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                conn.commit()
                return cur.rowcount > 0

    def set_email_verified(self) -> bool:
        sql = "UPDATE user_profile SET email_verified = 1 WHERE id = 1"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                conn.commit()
                return cur.rowcount > 0
