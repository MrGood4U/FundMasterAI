from okx.api import Account
from okx.app import OkxSPOT
from okx.app.utils import eprint
import pandas as pd
import numpy as np
import time
import datetime
import json
from . import config

class OkxApi:
    def __init__(self):

        # 行情数据无需添加key、secret与passphrase
        self.key = config.get_okx_api_key()
        self.secret = config.get_okx_api_secret()
        self.passphrase = config.get_okx_api_pass()
        # 使用http和https代理，proxies={'http':'xxxxx','https:':'xxxxx'}，与requests中的proxies参数规则相同
        self.proxies = {}
        # 转发：需搭建转发服务器，可参考：https://github.com/pyted/okx_resender
        self.proxy_host = None
        # 实盘 模拟盘
        self.flag = '0'
        self.timeframe = "1m"
        self.account = Account(
            key=self.key, secret=self.secret, passphrase=self.passphrase, flag=self.flag, proxies=self.proxies, proxy_host=self.proxy_host,
        )

        okx_spot = OkxSPOT(
            key=self.key, secret=self.secret, passphrase=self.passphrase, proxies=self.proxies, proxy_host=self.proxy_host,
        )
        self.spot_market = okx_spot.market
    
    SYMBOL_MAP = {
        "BTC_USDT": "BTC-USDT",
        "BTC": "BTC-USDT",
        "ETH_USDT": "ETH-USDT",
        "ETH": "ETH-USDT",
        "SOL_USDT": "SOL-USDT",
        "SOL": "SOL-USDT",
        "DOGE_USDT": "DOGE-USDT",
        "DOGE": "DOGE-USDT",
        "ADA_USDT": "ADA-USDT",
        "ADA": "ADA-USDT",
        "BNB_USDT": "BNB-USDT",
        "BNB": "BNB-USDT",
        "XRP_USDT": "XRP-USDT",
        "XRP": "XRP-USDT",
        "MATIC_USDT": "MATIC-USDT",
        "MATIC": "MATIC-USDT",
        "LINK_USDT": "LINK-USDT",
        "LINK": "LINK-USDT",
        "TRUMP_USDT": "TRUMP-USDT",
        "TRUMP": "TRUMP-USDT",
        "UNI_USDT": "UNI-USDT",
        "UNI": "UNI-USDT",
    }
    
    def preset_symbol(self, symbol):
        if symbol in self.SYMBOL_MAP:
            return self.SYMBOL_MAP[symbol]
        return symbol
    
    def get_books(self, symbol):
        symbol = self.preset_symbol(symbol)
        
        market = self.spot_market
        
        get_books_result = market.get_books(instId=symbol)

        result = {}
        result["bids"] = []
        for item in get_books_result["data"]["bids"]:
            result["bids"].append([float(item[0]), float(item[1])])
        result["asks"] = []
        for item in get_books_result["data"]["asks"]:
            result["asks"].append([float(item[0]), float(item[1])])
        
        return result
    
    def get_ticker(self, symbol):
        symbol = self.preset_symbol(symbol)
        
        market = self.spot_market
        
        old_d = market.get_ticker(instId=symbol)["data"]
        new_d = {}

        new_d["symbol"] = symbol
        new_d["last_price"] = float(old_d["last"])
        new_d["high24h"] = float(old_d["high24h"])
        new_d["low24h"] = float(old_d["low24h"])
        new_d["volume24h"] = float(old_d["vol24h"])
        new_d["change_percent"] = (float(old_d["last"]) - float(old_d["open24h"])) / float(old_d["open24h"])
        return new_d


    def fetch_klines(self, symbol, market_type, interval, start_time, end_time, limit = 1000):
        symbol = self.preset_symbol(symbol)

        start_time_str = datetime.datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
        end_time_str = datetime.datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")

        print(start_time_str, end_time_str)

        if market_type == "SPOT":
            market = self.spot_market
        else:
            market = None

        candle_result = market.get_history_candle(
            instId = symbol,
            start = start_time_str,
            end = end_time_str,
            bar= interval
        )
        candle = candle_result['data']
        df = market.candle_to_df(candle)
        kline_list = json.loads(df.to_json(orient='records', force_ascii=False))
        kline_list = kline_list[-1000:]

        result = []
        for d in kline_list:
            new_d = {}
            if "ts" in d:
                new_d["start_time"] = d["ts"]
            if "o" in d:
                new_d["open_price"] = d["o"]
            if "h" in d:
                new_d["high_price"] = d["h"]
            if "l" in d:
                new_d["low_price"] = d["l"]
            if "c" in d:
                new_d["close_price"] = d["c"]
            if "vol" in d:
                new_d["volume"] = d["vol"]
            if "volCcy" in d:
                new_d["volume_currency"] = d["volCcy"]
            result.append(new_d)

        return result

    def get_ma(self, symbol, market_type='SPOT', interval='1m', ma_periods=[5, 10, 20], start_time=0, end_time=0, limit=500):
        symbol = self.preset_symbol(symbol)

        if ma_periods is None or ma_periods == []:
            ma_periods = [5, 10, 20]
        if isinstance(ma_periods, str):
            try:
                ma_periods = [int(x) for x in ma_periods.split(',') if x.strip()]
            except Exception:
                ma_periods = [5, 10, 20]

        ma_periods = [int(x) for x in ma_periods]
        if len(ma_periods) == 0:
            ma_periods = [5, 10, 20]

        ma_periods_len = len(ma_periods)

        if end_time == 0:
            end_time = int(time.time())
        max_period = max(ma_periods)
        def interval_to_seconds(iv):
            iv = str(iv).lower().strip()
            try:
                if iv.endswith('m'):
                    return int(iv[:-1]) * 60
                if iv.endswith('h'):
                    return int(iv[:-1]) * 3600
                if iv.endswith('d'):
                    return int(iv[:-1]) * 86400
                if iv.endswith('s'):
                    return int(iv[:-1])
            except Exception:
                pass
            try:
                return int(iv) * 60
            except Exception:
                return 60

        seconds_per_bar = interval_to_seconds(interval)

        if start_time == 0:
            bars_to_fetch = max_period * 3
            start_time = end_time - bars_to_fetch * seconds_per_bar
        
        
        if end_time - start_time < max_period * seconds_per_bar:
            raise Exception("[end_time - start_time] is less than [interval]")

        klines = self.fetch_klines(symbol, market_type, interval, start_time, end_time, limit)

        df = pd.DataFrame(klines)
        if df.empty or 'close_price' not in df.columns:
            return []

        df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce')
        if 'start_time' in df.columns:
            df = df.sort_values('start_time')
        for p in ma_periods:
            col = f"ma_{p}"
            df[col] = df['close_price'].rolling(window=int(p), min_periods=int(p)).mean()

        result = {
            'symbol': symbol,
            'interval': interval,
            'ma_periods': ma_periods,
            'items': []
        }

        for _, row in df.iterrows():
            ma_list = []
            for p in ma_periods:
                col = f"ma_{p}"
                val = row[col] if col in row else None
                if pd.isna(val):
                    ma_list.append(None)
                else:
                    ma_list.append(round(float(val), 4))

            result['items'].append({
                'datetime': row['start_time'] if 'start_time' in row else None,
                'close_price': float(row['close_price']) if not pd.isna(row['close_price']) else None,
                'ma': ma_list
            })

        return result

if __name__ == "__main__":
    bot = OkxApi()
    # print(bot.get_ma('ADA', 'SPOT', '1H', [5], 0, 0, 500))