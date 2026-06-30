from forex_python.converter import CurrencyRates, CurrencyCodes
from datetime import datetime

class ForexAPI:
    def __init__(self):
        self.currency_rates = CurrencyRates()
        self.currency_codes = CurrencyCodes()

    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        self.currency_rates = CurrencyRates()
        return self.currency_rates.get_rate(from_currency, to_currency)

    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        self.currency_rates = CurrencyRates()
        return self.currency_rates.convert(from_currency, to_currency, amount)
    
    def get_all_rates(self, base_currency: str) -> dict:
        self.currency_rates = CurrencyRates()
        return self.currency_rates.get_rates(base_currency)

    def get_history_rates(self, from_currency: str, to_currency: str, query_date: datetime) -> dict:
        self.currency_rates = CurrencyRates()
        return self.currency_rates.get_rates(from_currency, to_currency, query_date)