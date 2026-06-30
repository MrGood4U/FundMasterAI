import yfinance as yf
import pandas as pd
from typing import Optional, List, Dict, Any


# 常用全球指数代码
GLOBAL_INDICES = {
    "^GSPC":    {"name": "S&P 500",              "region": "美国",   "currency": "USD"},
    "^IXIC":    {"name": "纳斯达克综合指数",       "region": "美国",   "currency": "USD"},
    "^DJI":     {"name": "道琼斯工业平均指数",     "region": "美国",   "currency": "USD"},
    "^RUT":     {"name": "罗素2000指数",           "region": "美国",   "currency": "USD"},
    "^FTSE":    {"name": "英国富时100指数",        "region": "英国",   "currency": "GBP"},
    "^N225":    {"name": "日经225指数",            "region": "日本",   "currency": "JPY"},
    "^HSI":     {"name": "恒生指数",               "region": "香港",   "currency": "HKD"},
    "^GDAXI":   {"name": "德国DAX指数",            "region": "德国",   "currency": "EUR"},
    "^FCHI":    {"name": "法国CAC40指数",          "region": "法国",   "currency": "EUR"},
    "^STOXX50E":{"name": "欧洲斯托克50指数",       "region": "欧洲",   "currency": "EUR"},
    "^AXJO":    {"name": "澳大利亚ASX200指数",     "region": "澳大利亚","currency": "AUD"},
    "^KS11":    {"name": "韩国KOSPI指数",          "region": "韩国",   "currency": "KRW"},
    "^NSEI":    {"name": "印度NIFTY50指数",        "region": "印度",   "currency": "INR"},
    "^BVSP":    {"name": "巴西BOVESPA指数",        "region": "巴西",   "currency": "BRL"},
}


class YFinanceAPI:
    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # 全球指数 — 基本信息
    # ------------------------------------------------------------------

    def get_index_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取全球指数的详细信息（名称、市值、PE等）"""
        try:
            t = yf.Ticker(ticker)
            info = t.info
            if not info or info.get("regularMarketPrice") is None:
                return None
            return {
                "ticker": ticker,
                "name": info.get("shortName") or info.get("longName"),
                "price": info.get("regularMarketPrice"),
                "previous_close": info.get("regularMarketPreviousClose"),
                "open": info.get("regularMarketOpen"),
                "day_high": info.get("regularMarketDayHigh"),
                "day_low": info.get("regularMarketDayLow"),
                "volume": info.get("regularMarketVolume"),
                "change": info.get("regularMarketChange"),
                "change_pct": info.get("regularMarketChangePercent"),
                "fifty_day_avg": info.get("fiftyDayAverage"),
                "two_hundred_day_avg": info.get("twoHundredDayAverage"),
                "currency": info.get("currency"),
                "market": info.get("market"),
                "exchange": info.get("exchangeName") or info.get("fullExchangeName"),
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 全球指数 — 最新行情
    # ------------------------------------------------------------------

    def get_index_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取全球指数的最新报价（精简版）"""
        try:
            t = yf.Ticker(ticker)
            # fast_info 比 info 更快，字段更稳定
            fi = t.fast_info
            price = fi.get("lastPrice")
            if price is None:
                # 回退到 info
                info = t.info
                price = info.get("regularMarketPrice")
                if price is None:
                    return None
                return {
                    "ticker": ticker,
                    "name": info.get("shortName") or info.get("longName"),
                    "price": price,
                    "previous_close": info.get("regularMarketPreviousClose"),
                    "open": info.get("regularMarketOpen"),
                    "day_high": info.get("regularMarketDayHigh"),
                    "day_low": info.get("regularMarketDayLow"),
                    "volume": info.get("regularMarketVolume"),
                    "change": info.get("regularMarketChange"),
                    "change_pct": info.get("regularMarketChangePercent"),
                    "currency": info.get("currency"),
                }
            return {
                "ticker": ticker,
                "name": t.info.get("shortName") if t.info else None,
                "price": price,
                "previous_close": fi.get("previousClose"),
                "open": fi.get("open"),
                "day_high": fi.get("dayHigh"),
                "day_low": fi.get("dayLow"),
                "volume": fi.get("lastVolume"),
                "change": (price - fi.get("previousClose", price)) if fi.get("previousClose") else None,
                "change_pct": ((price - fi["previousClose"]) / fi["previousClose"] * 100)
                              if fi.get("previousClose") and fi["previousClose"] != 0 else None,
                "currency": fi.get("currency"),
            }
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
            t = yf.Ticker(ticker)
            if start_date and end_date:
                df = t.history(start=start_date, end=end_date, interval=interval)
            else:
                df = t.history(period=period, interval=interval)

            if df is None or df.empty:
                return None

            # 重置索引，把 Date 变为列
            df = df.reset_index()
            # 统一列名
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            return df
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 全球指数 — 列表
    # ------------------------------------------------------------------

    def get_supported_indices(self) -> List[Dict[str, str]]:
        """返回支持的全球指数列表"""
        return [
            {"ticker": k, "name": v["name"], "region": v["region"], "currency": v["currency"]}
            for k, v in GLOBAL_INDICES.items()
        ]
