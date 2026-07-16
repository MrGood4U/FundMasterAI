"""资产配置服务：当前配置、目标配置、偏离度计算。"""

from services.holding_service import HoldingService
from daos.allocation_dao import AllocationDao

# 四大类资产
ASSET_CLASSES = ["stock", "fund", "bond", "crypto"]

# 偏离度阈值（百分比），超过此值视为显著偏离
DRIFT_THRESHOLD = 5.0


class AllocationService:
    def __init__(self):
        self.holding_svc = HoldingService()
        self.dao = AllocationDao()

    # ------------------------------------------------------------------
    # 当前配置
    # ------------------------------------------------------------------

    def get_current_allocation(self) -> dict:
        """返回当前各类资产持仓市值与占比。"""
        holdings = self.holding_svc.get_holdings(page=1, page_size=999999)
        items = holdings.get("items", [])

        # 按 asset_type 汇总
        by_type = {k: {"market_value": 0.0, "total_cost": 0.0} for k in ASSET_CLASSES}
        total_mv = 0.0
        total_cost = 0.0

        for h in items:
            at = h.get("asset_type", "other")
            if at not in by_type:
                by_type[at] = {"market_value": 0.0, "total_cost": 0.0}
            mv = float(h.get("market_value") or 0)
            cost = float(h.get("total_cost") or 0)
            by_type[at]["market_value"] += mv
            by_type[at]["total_cost"] += cost
            total_mv += mv
            total_cost += cost

        allocation = []
        for at in sorted(by_type.keys()):
            mv = by_type[at]["market_value"]
            pct = round(mv / total_mv * 100, 2) if total_mv > 0 else 0.0
            allocation.append({
                "asset_type": at,
                "market_value": round(mv, 2),
                "pct": pct,
                "total_cost": round(by_type[at]["total_cost"], 2),
            })

        return {
            "items": allocation,
            "total_market_value": round(total_mv, 2),
            "total_cost": round(total_cost, 2),
        }

    # ------------------------------------------------------------------
    # 目标配置
    # ------------------------------------------------------------------

    def set_target_allocation(self, targets: dict) -> dict:
        """设置目标配置百分比。

        Args:
            targets: {"stock": 40, "fund": 30, "bond": 20, "crypto": 10}
        """
        # 校验
        if not targets or not isinstance(targets, dict):
            return {"error": "targets must be a non-empty dict"}

        total = 0.0
        for at, pct in targets.items():
            if at not in ASSET_CLASSES:
                return {"error": f"unknown asset_type: {at}, must be one of {ASSET_CLASSES}"}
            try:
                pct_val = float(pct)
            except (TypeError, ValueError):
                return {"error": f"target_pct for {at} must be a number"}
            total += pct_val

        if abs(total - 100) > 0.01:
            return {"error": f"target percentages sum to {total}, must sum to 100"}

        for at, pct in targets.items():
            self.dao.upsert(at, float(pct))

        return {"targets": targets, "message": "ok"}

    def get_target_allocation(self) -> dict:
        """读取已保存的目标配置。"""
        rows = self.dao.get_all()
        result = {}
        for r in rows:
            result[r["asset_type"]] = float(r["target_pct"])
        return result

    # ------------------------------------------------------------------
    # 偏离度
    # ------------------------------------------------------------------

    def get_drift(self) -> dict:
        """计算当前配置与目标配置的偏离度。"""
        current = self.get_current_allocation()
        current_map = {item["asset_type"]: item["pct"] for item in current["items"]}

        target = self.get_target_allocation()

        drift_items = []
        for at in ASSET_CLASSES:
            cur_pct = current_map.get(at, 0.0)
            tgt_pct = target.get(at, 0.0)
            diff = round(cur_pct - tgt_pct, 2)

            if abs(diff) < DRIFT_THRESHOLD:
                status = "正常"
            elif diff > 0:
                status = "超配"
            else:
                status = "低配"

            drift_items.append({
                "asset_type": at,
                "current_pct": cur_pct,
                "target_pct": tgt_pct,
                "diff_pct": diff,
                "status": status,
            })

        return {
            "items": drift_items,
            "total_market_value": current["total_market_value"],
        }
