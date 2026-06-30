import finshare as fs

class FinshareStockAPI:
    def __init__(self):
        pass

    def date_str_verify(self, date_str: str):
        # YYYYMMDD格式验证
        if len(date_str) != 8 or not date_str.isdigit():
            return False
        return True

    def get_stock_flow(self, stock_code: str):
        return fs.get_money_flow(stock_code)

    def get_stock_flow_industry(self):
        return fs.get_money_flow_industry()
    
    # 获取龙虎榜
    def get_stock_lhb(self, start_date: str, end_date: str):
        if not self.date_str_verify(start_date) or not self.date_str_verify(end_date):
            return None
        return fs.get_lhb(start_date, end_date)
    
    # 获取具体股票的龙虎榜明细
    def get_stock_lhb_detail(self, stock_code: str, trade_date: str):
        if not self.date_str_verify(trade_date):
            return None
        return fs.get_lhb_detail(stock_code, trade_date)