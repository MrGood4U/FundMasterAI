import logging
from typing import Any, Dict, List, Optional

from apis.akshare_macro_api import AkshareMacro

logger = logging.getLogger(__name__)


class MacroService:
    """宏观数据服务"""

    def __init__(self):
        self.macro = AkshareMacro()

    # ------------------------------------------------------------------
    # 国家 / 指标 元信息
    # ------------------------------------------------------------------

    def get_supported_countries(self) -> List[Dict[str, Any]]:
        """返回支持的国家列表"""
        return self.macro.get_supported_countries()

    def get_indicator_list(self, country: Optional[str] = None) -> Dict[str, Any]:
        """返回指定国家（或全部）的指标列表"""
        return self.macro.get_indicator_list(country)

    def get_indicator_schema(self, country: str, indicator: str) -> Optional[Dict[str, Any]]:
        """返回指定指标的完整 schema（含输出列定义）"""
        return self.macro.get_indicator_schema(country, indicator)

    # ------------------------------------------------------------------
    # 宏观数据查询
    # ------------------------------------------------------------------

    def get_macro_data(self, country: str, indicator: str,
                       **kwargs) -> List[Dict[str, Any]]:
        """获取宏观数据，返回 list-of-dicts"""
        try:
            df = self.macro.get_macro_data(country, indicator, **kwargs)
            if df is None or df.empty:
                return []
            return df.to_dict(orient="records")
        except Exception as e:
            logger.error("MacroService.get_macro_data(%s/%s) failed: %s",
                         country, indicator, e)
            return []
