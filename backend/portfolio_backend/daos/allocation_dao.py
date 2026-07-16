"""资产配置目标表 CRUD。"""

from daos.base_dao import get_connection


class AllocationDao:

    def upsert(self, asset_type: str, target_pct: float) -> bool:
        """插入或更新单条目标配置。"""
        sql = """
            INSERT INTO allocation_target (asset_type, target_pct)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE target_pct = VALUES(target_pct)
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (asset_type, target_pct))
                conn.commit()
                return cur.rowcount > 0

    def get_all(self) -> list:
        """获取全部目标配置。"""
        sql = "SELECT asset_type, target_pct FROM allocation_target ORDER BY asset_type"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()

    def delete(self, asset_type: str) -> bool:
        """删除某类资产的目标配置。"""
        sql = "DELETE FROM allocation_target WHERE asset_type = %s"
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (asset_type,))
                conn.commit()
                return cur.rowcount > 0
