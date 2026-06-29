import efinance as ef

from flask import current_app

from apis.field_mapping import (
    apply_mapping,
    FUND_QUOTE_HISTORY_MAP
)

class EfinanceAPI:
    def __init__(self):
        pass
    
    def get_hist(self, code: str):
        df = ef.fund.get_quote_history(code)
        return apply_mapping(df, FUND_QUOTE_HISTORY_MAP)

    def hist(self, code: str):
        return self.get_hist(code)