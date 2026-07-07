import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd

from apis.forex_api import ForexAPI
from apis.openbb_api import OpenBBAPI
from apis.yfinance_api import YFinanceAPI
from daos.cache_dao import CacheDao

logger = logging.getLogger(__name__)


class GlobalService:
    """全球市场服务 — 外汇汇率 + 全球指数"""

    def __init__(self):
        self.forex = ForexAPI()
        self.yf = YFinanceAPI()
        self.obb = OpenBBAPI()
        self.cache = CacheDao.from_config()

    # ==================================================================
    # 外汇 — 汇率查询
    # ==================================================================

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """查询两种货币之间的汇率"""
        try:
            rate = self.forex.get_exchange_rate(from_currency.upper(), to_currency.upper())
            return rate
        except Exception as e:
            logger.warning("GlobalService.get_exchange_rate(%s→%s) failed: %s",
                           from_currency, to_currency, e)
            return None

    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """将金额从一种货币转换为另一种货币"""
        try:
            result = self.forex.convert_currency(
                amount, from_currency.upper(), to_currency.upper()
            )
            return result
        except Exception as e:
            logger.warning("GlobalService.convert_currency(%s %s→%s) failed: %s",
                           amount, from_currency, to_currency, e)
            return None

    def get_all_rates(self, base_currency: str) -> Optional[Dict[str, float]]:
        """获取基础货币对所有其他货币的汇率"""
        try:
            rates = self.forex.get_all_rates(base_currency.upper())
            return rates
        except Exception as e:
            logger.warning("GlobalService.get_all_rates(%s) failed: %s", base_currency, e)
            return None

    def get_history_rates(self, from_currency: str, to_currency: str,
                          query_date: str) -> Optional[Dict[str, float]]:
        """查询历史某天的汇率（同时返回 from→其他 全部汇率）"""
        try:
            dt = datetime.strptime(query_date, "%Y-%m-%d")
            rates = self.forex.get_history_rates(
                from_currency.upper(), to_currency.upper(), dt
            )
            return rates
        except Exception as e:
            logger.warning("GlobalService.get_history_rates(%s→%s, %s) failed: %s",
                           from_currency, to_currency, query_date, e)
            return None

    # ==================================================================
    # 全球指数 — 查询
    # ==================================================================

    def get_index_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取单个全球指数的最新行情（yfinance 优先，失败时用 OpenBB 兜底）"""
        ticker_upper = ticker.upper()
        try:
            result = self.yf.get_index_quote(ticker_upper)
            if result is not None:
                return result
        except Exception as e:
            logger.warning("GlobalService.get_index_quote(%s) yfinance failed: %s", ticker_upper, e)

        # OpenBB 兜底
        try:
            logger.info("GlobalService.get_index_quote(%s) falling back to OpenBB", ticker_upper)
            return self.obb.get_index_quote(ticker_upper)
        except Exception as e:
            logger.warning("GlobalService.get_index_quote(%s) OpenBB also failed: %s", ticker_upper, e)
            return None

    def get_index_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取单个全球指数的详细信息（yfinance 优先，失败时用 OpenBB 兜底）"""
        ticker_upper = ticker.upper()
        try:
            result = self.yf.get_index_info(ticker_upper)
            if result is not None:
                return result
        except Exception as e:
            logger.warning("GlobalService.get_index_info(%s) yfinance failed: %s", ticker_upper, e)

        # OpenBB 兜底
        try:
            logger.info("GlobalService.get_index_info(%s) falling back to OpenBB", ticker_upper)
            return self.obb.get_index_info(ticker_upper)
        except Exception as e:
            logger.warning("GlobalService.get_index_info(%s) OpenBB also failed: %s", ticker_upper, e)
            return None

    def get_multiple_quotes(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """批量获取多个全球指数的最新行情（yfinance 优先，失败时用 OpenBB 兜底）"""
        upper_tickers = [t.upper() for t in tickers]
        try:
            result = self.yf.get_multiple_quotes(upper_tickers)
            if result:
                return result
        except Exception as e:
            logger.warning("GlobalService.get_multiple_quotes(%s) yfinance failed: %s", upper_tickers, e)

        # OpenBB 兜底
        try:
            logger.info("GlobalService.get_multiple_quotes(%s) falling back to OpenBB", upper_tickers)
            return self.obb.get_multiple_quotes(upper_tickers)
        except Exception as e:
            logger.warning("GlobalService.get_multiple_quotes(%s) OpenBB also failed: %s", upper_tickers, e)
            return []

    def get_index_hist(self, ticker: str, period: str = "1mo",
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       interval: str = "1d") -> List[Dict[str, Any]]:
        """获取全球指数的历史K线数据（yfinance 优先，失败时用 OpenBB 兜底）"""
        ticker_upper = ticker.upper()
        try:
            df = self.yf.get_index_hist(
                ticker_upper, period=period,
                start_date=start_date, end_date=end_date, interval=interval,
            )
            if df is not None and not df.empty:
                return df.to_dict(orient="records")
        except Exception as e:
            logger.warning("GlobalService.get_index_hist(%s) yfinance failed: %s", ticker_upper, e)

        # OpenBB 兜底
        try:
            logger.info("GlobalService.get_index_hist(%s) falling back to OpenBB", ticker_upper)
            df = self.obb.get_index_hist(
                ticker_upper, period=period,
                start_date=start_date, end_date=end_date, interval=interval,
            )
            if df is None or df.empty:
                return []
            return df.to_dict(orient="records")
        except Exception as e:
            logger.warning("GlobalService.get_index_hist(%s) OpenBB also failed: %s", ticker_upper, e)
            return []

    def get_index_rank(self) -> List[Dict[str, Any]]:
        """获取所有全球指数的涨跌幅排行（change_pct 从高到低，优先读缓存）

        数据源优先级: 缓存 → yfinance → OpenBB
        """
        cache_key = "global:index:rank"
        try:
            df = self.cache.get_df(cache_key)
            if df is not None and not df.empty:
                return df.to_dict(orient="records")
        except Exception as e:
            logger.warning("GlobalService.get_index_rank() cache read failed: %s", e)

        # 优先 yfinance
        try:
            data = self.yf.get_all_indices_ranked()
            if data:
                try:
                    self.cache.set_df(cache_key, pd.DataFrame(data))
                except Exception:
                    pass
                return data
        except Exception as e:
            logger.warning("GlobalService.get_index_rank() yfinance failed: %s", e)

        # OpenBB 兜底
        try:
            logger.info("GlobalService.get_index_rank() falling back to OpenBB")
            data = self.obb.get_all_indices_ranked()
            if data:
                try:
                    self.cache.set_df(cache_key, pd.DataFrame(data))
                except Exception:
                    pass
            return data
        except Exception as e:
            logger.warning("GlobalService.get_index_rank() OpenBB also failed: %s", e)
            return []

    def get_supported_indices(self) -> List[Dict[str, str]]:
        """返回支持的全球指数列表"""
        return self.yf.get_supported_indices()
