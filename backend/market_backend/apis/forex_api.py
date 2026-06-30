from forex_python.converter import CurrencyRates, CurrencyCodes
from currency_converter import CurrencyConverter
from datetime import datetime
import threading

class ForexAPI:
    def __init__(self):
        self.currency_rates = CurrencyRates()
        self.currency_converter = CurrencyConverter()
        self.currency_codes = CurrencyCodes()
        self.timeout = 3

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        self.currency_rates = CurrencyRates()
        self.currency_converter = CurrencyConverter()
        # 如果currency_rates超过5秒没有响应，则使用currency_converter作为备用
        result = []
        def _fetch():
            try:
                result.append(self.currency_rates.get_rate(from_currency, to_currency))
            except Exception:
                pass

        t = threading.Thread(target=_fetch, daemon=True)
        t.start()
        t.join(timeout=self.timeout)
        if result and result[0]:
            rate = result[0]
        else:
            rate = self.currency_converter.convert(1, from_currency, to_currency)
        return rate

    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        self.currency_rates = CurrencyRates()
        self.currency_converter = CurrencyConverter()
        result = []
        def _fetch():
            try:
                result.append(self.currency_rates.convert(from_currency, to_currency, amount))
            except Exception:
                pass

        t = threading.Thread(target=_fetch, daemon=True)
        t.start()
        t.join(timeout=self.timeout)
        if result and result[0]:
            return result[0]
        else:
            return self.currency_converter.convert(amount, from_currency, to_currency)
    
    def get_all_rates(self, base_currency: str) -> dict:
        self.currency_rates = CurrencyRates()
        self.currency_converter = CurrencyConverter()
        result = []
        def _fetch():
            try:
                result.append(self.currency_rates.get_rates(base_currency))
            except Exception:
                pass

        t = threading.Thread(target=_fetch, daemon=True)
        t.start()
        t.join(timeout=self.timeout)
        if result and result[0]:
            return result[0]
        else:
            temp = {}
            rates_dict = self.currency_converter._rates
            for key in list(rates_dict):
                if key != base_currency:
                    try:
                        rate = self.currency_converter.convert(1, base_currency, key)
                        temp[key] = rate
                    except Exception:
                        continue
            return temp

    def get_history_rates(self, from_currency: str, to_currency: str, query_date: datetime) -> dict:
        self.currency_rates = CurrencyRates()
        return self.currency_rates.get_rates(from_currency, to_currency, query_date)