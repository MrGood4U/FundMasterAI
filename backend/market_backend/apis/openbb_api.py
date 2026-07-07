from datetime import date, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd
from openbb import obb


# 常用全球指数代码（与 yfinance_api 保持一致，便于直接替换）
GLOBAL_INDICES = {
    "^GSPC":     {"name": "S&P 500",              "region": "美国",     "currency": "USD"},
    "^IXIC":     {"name": "纳斯达克综合指数",       "region": "美国",     "currency": "USD"},
    "^DJI":      {"name": "道琼斯工业平均指数",     "region": "美国",     "currency": "USD"},
    "^RUT":      {"name": "罗素2000指数",           "region": "美国",     "currency": "USD"},
    "^FTSE":     {"name": "英国富时100指数",        "region": "英国",     "currency": "GBP"},
    "^N225":     {"name": "日经225指数",            "region": "日本",     "currency": "JPY"},
    "^HSI":      {"name": "恒生指数",               "region": "香港",     "currency": "HKD"},
    "^GDAXI":    {"name": "德国DAX指数",            "region": "德国",     "currency": "EUR"},
    "^FCHI":     {"name": "法国CAC40指数",          "region": "法国",     "currency": "EUR"},
    "^STOXX50E": {"name": "欧洲斯托克50指数",       "region": "欧洲",     "currency": "EUR"},
    "^AXJO":     {"name": "澳大利亚ASX200指数",     "region": "澳大利亚", "currency": "AUD"},
    "^KS11":     {"name": "韩国KOSPI指数",          "region": "韩国",     "currency": "KRW"},
    "^NSEI":     {"name": "印度NIFTY50指数",        "region": "印度",     "currency": "INR"},
    "^BVSP":     {"name": "巴西BOVESPA指数",        "region": "巴西",     "currency": "BRL"},
}


class OpenBBAPI:
    """全球指数数据源 — 基于 OpenBB SDK，作为 YFinance 失败时的替代数据源。

    OpenBB 默认的 provider 优先级为 fmp → intrinio → yfinance，
    不显式指定 provider 以利用其内置的多源容错机制。
    """

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _quote_to_dict(ticker: str, r) -> Optional[Dict[str, Any]]:
        """将 OpenBB equity.price.quote 的返回对象转为统一字典"""
        last_price = getattr(r, "last_price", None)
        prev_close = getattr(r, "prev_close", None)

        # 如果 last_price 为空（常见于非交易时段），
        # 尝试用 prev_close 作为当前价格
        if last_price is None:
            last_price = prev_close

        # 计算涨跌
        change = getattr(r, "change", None)
        change_pct = getattr(r, "change_percent", None)
        if (change is None or change_pct is None) and last_price is not None and prev_close is not None and prev_close != 0:
            change = last_price - prev_close
            change_pct = (change / prev_close) * 100

        return {
            "ticker": ticker,
            "name": getattr(r, "name", None),
            "price": last_price,
            "previous_close": prev_close,
            "open": getattr(r, "open", None),
            "day_high": getattr(r, "high", None),
            "day_low": getattr(r, "low", None),
            "volume": getattr(r, "volume", None),
            "change": change,
            "change_pct": change_pct,
            "fifty_day_avg": getattr(r, "ma_50d", None),
            "two_hundred_day_avg": getattr(r, "ma_200d", None),
            "currency": getattr(r, "currency", None),
            "exchange": getattr(r, "exchange", None),
        }

    @staticmethod
    def _latest_close_from_hist(ticker: str) -> Optional[Dict[str, Any]]:
        """通过最近 10 个自然日的历史数据获取最新收盘价，
        用于 equity.price.quote 返回空 last_price 时的降级方案。
        """
        try:
            today = date.today()
            start = today - timedelta(days=10)
            result = obb.index.price.historical(ticker, start_date=start, end_date=today)
            if result is None or not hasattr(result, "results") or not result.results:
                return None
            data = result.results
            if len(data) < 2:
                return None
            latest = data[-1]
            prev = data[-2]
            close = getattr(latest, "close", None)
            prev_close = getattr(prev, "close", None)
            if close is None:
                return None
            change = (close - prev_close) if prev_close is not None else None
            change_pct = ((close - prev_close) / prev_close * 100) if prev_close and prev_close != 0 else None
            return {
                "ticker": ticker,
                "name": None,
                "price": close,
                "previous_close": prev_close,
                "open": getattr(latest, "open", None),
                "day_high": getattr(latest, "high", None),
                "day_low": getattr(latest, "low", None),
                "volume": getattr(latest, "volume", None),
                "change": change,
                "change_pct": change_pct,
                "currency": None,
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 全球指数 — 基本信息
    # ------------------------------------------------------------------

    def get_index_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取全球指数的详细信息（名称、价格等）"""
        try:
            result = obb.equity.price.quote(ticker)
            if result is None or not hasattr(result, "results") or not result.results:
                return None
            r = result.results[0] if isinstance(result.results, list) else result.results
            base = self._quote_to_dict(ticker, r)

            # 尝试通过 equity.profile 补充更多信息（PE、市值等指数通常没有）
            try:
                profile = obb.equity.profile(ticker)
                if profile and hasattr(profile, "results") and profile.results:
                    p = profile.results[0] if isinstance(profile.results, list) else profile.results
                    base["market"] = getattr(p, "sector", None)
                    base["exchange"] = base.get("exchange") or getattr(p, "stock_exchange", None)
            except Exception:
                pass

            # 如果 last_price 仍然为空，用历史数据兜底
            if base.get("price") is None:
                hist = self._latest_close_from_hist(ticker)
                if hist:
                    base["price"] = hist["price"]
                    base["previous_close"] = base["previous_close"] or hist["previous_close"]
                    base["change"] = base["change"] or hist["change"]
                    base["change_pct"] = base["change_pct"] or hist["change_pct"]

            if base.get("price") is None:
                return None
            return base
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 全球指数 — 最新行情
    # ------------------------------------------------------------------

    def get_index_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取全球指数的最新报价（精简版）"""
        try:
            result = obb.equity.price.quote(ticker)
            if result is None or not hasattr(result, "results") or not result.results:
                return None
            r = result.results[0] if isinstance(result.results, list) else result.results
            base = self._quote_to_dict(ticker, r)

            # 如果 last_price 为空，用历史数据兜底
            if base.get("price") is None:
                hist = self._latest_close_from_hist(ticker)
                if hist:
                    base["price"] = hist["price"]
                    base["previous_close"] = base["previous_close"] or hist["previous_close"]
                    base["open"] = base["open"] or hist["open"]
                    base["day_high"] = base["day_high"] or hist["day_high"]
                    base["day_low"] = base["day_low"] or hist["day_low"]
                    base["volume"] = base["volume"] or hist["volume"]
                    base["change"] = base["change"] or hist["change"]
                    base["change_pct"] = base["change_pct"] or hist["change_pct"]

            if base.get("price") is None:
                return None
            return base
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 全球指数 — 批量行情
    # ------------------------------------------------------------------

    def get_multiple_quotes(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """批量获取多个全球指数的最新报价"""
        results = []
        for ticker in tickers:
            quote = self.get_index_quote(ticker)
            if quote is not None:
                # 用元数据补充名称和地区
                meta = GLOBAL_INDICES.get(ticker.upper(), {})
                if meta.get("name"):
                    quote["name"] = quote.get("name") or meta["name"]
                quote["region"] = meta.get("region")
                results.append(quote)
        return results

    # ------------------------------------------------------------------
    # 全球指数 — 历史数据
    # ------------------------------------------------------------------

    def get_index_hist(
        self,
        ticker: str,
        period: str = "1mo",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
    ) -> Optional[pd.DataFrame]:
        """获取全球指数的历史K线数据

        Parameters
        ----------
        ticker : str
            指数代码，如 "^GSPC"
        period : str
            数据周期，可选 "1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"
        start_date : str, optional
            起始日期 "YYYY-MM-DD"，与 period 互斥
        end_date : str, optional
            结束日期 "YYYY-MM-DD"
        interval : str
            K线周期，可选 "1d","1wk","1mo","1h","1m" 等
        """
        try:
            # yfinance 和 OpenBB 的 interval 格式不同，做一层转换
            _INTERVAL_MAP = {
                "1wk": "1W", 
                "1mo": "1M", 
                "3mo": "1Q",
            }
            obb_interval = _INTERVAL_MAP.get(interval, interval)

            if start_date and end_date:
                result = obb.index.price.historical(
                    ticker,
                    start_date=start_date,
                    end_date=end_date,
                    interval=obb_interval,
                )
            else:
                # OpenBB 没有 period 参数，需要自己根据 period 计算 start_date
                today = date.today()
                period_days = {
                    "1d": 1, "5d": 7, "1mo": 35, "3mo": 100,
                    "6mo": 190, "1y": 370, "2y": 740,
                    "5y": 1850, "10y": 3700, "ytd": 370, "max": 7300,
                }
                days = period_days.get(period, 35)
                calc_start = today - timedelta(days=days)
                result = obb.index.price.historical(
                    ticker,
                    start_date=calc_start.strftime("%Y-%m-%d"),
                    end_date=today.strftime("%Y-%m-%d"),
                    interval=obb_interval,
                )

            if result is None or not hasattr(result, "results") or not result.results:
                return None

            data = result.results
            # 转为 DataFrame
            rows = []
            for item in data:
                rows.append({
                    "date": getattr(item, "date", None),
                    "open": getattr(item, "open", None),
                    "high": getattr(item, "high", None),
                    "low": getattr(item, "low", None),
                    "close": getattr(item, "close", None),
                    "volume": getattr(item, "volume", None),
                })

            df = pd.DataFrame(rows)
            if df.empty:
                return None
            return df
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 全球指数 — 列表
    # ------------------------------------------------------------------

    def get_all_indices_ranked(self) -> List[Dict[str, Any]]:
        """获取所有全球指数的行情，按涨跌幅 (change_pct) 从高到低排序"""
        results = []
        for ticker, meta in GLOBAL_INDICES.items():
            quote = self.get_index_quote(ticker)
            if quote is None:
                # 降级：用 get_index_info 作为备选
                quote = self.get_index_info(ticker)
            if quote is None:
                continue
            # 用元数据补充名称和地区
            quote["name"] = quote.get("name") or meta["name"]
            quote["region"] = meta.get("region", "")
            quote["currency"] = quote.get("currency") or meta.get("currency", "")
            results.append(quote)

        # 按 change_pct 从大到小排序 (None 排到最后)
        results.sort(
            key=lambda x: x.get("change_pct") if x.get("change_pct") is not None else float("-inf"),
            reverse=True,
        )
        return results

    def get_supported_indices(self) -> List[Dict[str, str]]:
        """返回支持的全球指数列表"""
        return [
            {"ticker": k, "name": v["name"], "region": v["region"], "currency": v["currency"]}
            for k, v in GLOBAL_INDICES.items()
        ]
