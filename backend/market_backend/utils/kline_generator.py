import pandas as pd
import numpy as np


class KLineGenerator:
    """通用K线技术指标生成器。

    接收包含 OHLC 列的 DataFrame，在其基础上追加 MA / MACD / RSI / KDJ / BOLL
    指标列，返回新的 DataFrame。调用方可自行决定 to_dict / to_json 等序列化方式。
    """

    def __init__(self, df: pd.DataFrame, price_col: str = "close"):
        if df is None or df.empty:
            raise ValueError("df must not be None or empty")
        if price_col not in df.columns:
            raise ValueError(f"price_col '{price_col}' not in DataFrame columns")
        self.df = df.copy()
        self.price_col = price_col

    # ------------------------------------------------------------------
    # 单一指标
    # ------------------------------------------------------------------

    def ma(self, periods: list = None) -> pd.DataFrame:
        """移动平均线。默认 MA5 / MA10 / MA20 / MA60。"""
        if periods is None:
            periods = [5, 10, 20, 60]
        close = self.df[self.price_col].astype(float)
        for p in periods:
            self.df[f"ma{p}"] = close.rolling(window=p).mean()
        return self.df

    def macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """MACD：DIF / DEA / 柱状值。"""
        close = self.df[self.price_col].astype(float)
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        self.df["macd_dif"] = ema_fast - ema_slow
        self.df["macd_dea"] = self.df["macd_dif"].ewm(span=signal, adjust=False).mean()
        self.df["macd_bar"] = 2 * (self.df["macd_dif"] - self.df["macd_dea"])
        return self.df

    def rsi(self, period: int = 14) -> pd.DataFrame:
        """RSI 相对强弱指标（Wilder smoothing via EWM alpha）。"""
        close = self.df[self.price_col].astype(float)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
        rs = avg_gain / avg_loss
        self.df["rsi"] = 100 - (100 / (1 + rs))
        return self.df

    def kdj(self, n: int = 9, k_smooth: int = 3, d_smooth: int = 3) -> pd.DataFrame:
        """KDJ 随机指标。需要 high / low 列。"""
        close = self.df[self.price_col].astype(float)
        if "high" not in self.df.columns or "low" not in self.df.columns:
            high = close
            low = close
        else:
            high = self.df["high"].astype(float)
            low = self.df["low"].astype(float)
        

        lowest_low = low.rolling(window=n).min()
        highest_high = high.rolling(window=n).max()
        rsv = ((close - lowest_low) / (highest_high - lowest_low)) * 100
        rsv = rsv.fillna(50)

        self.df["kdj_k"] = rsv.ewm(alpha=1 / k_smooth, adjust=False).mean()
        self.df["kdj_d"] = self.df["kdj_k"].ewm(alpha=1 / d_smooth, adjust=False).mean()
        self.df["kdj_j"] = 3 * self.df["kdj_k"] - 2 * self.df["kdj_d"]
        return self.df

    def boll(self, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """布林带：上轨 / 中轨 / 下轨。"""
        close = self.df[self.price_col].astype(float)
        mid = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        self.df["boll_mid"] = mid
        self.df["boll_upper"] = mid + std_dev * std
        self.df["boll_lower"] = mid - std_dev * std
        return self.df

    # ------------------------------------------------------------------
    # 批量
    # ------------------------------------------------------------------

    def all(self) -> pd.DataFrame:
        """一次性计算所有指标（MA / MACD / RSI / KDJ / BOLL）。"""
        self.ma()
        self.macd()
        self.rsi()
        self.kdj()
        self.boll()
        return self.df
