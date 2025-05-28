from atlasbot.config import MAX_GROSS_USD, MAX_DAILY_LOSS

class RiskManager:
    def __init__(self):
        self.positions = {}
        self.daily_pnl = 0.0

    def update_position(self, symbol: str, delta_usd: float):
        self.positions[symbol] = self.positions.get(symbol, 0.0) + delta_usd

    def add_pnl(self, amount: float):
        self.daily_pnl += amount

    def gross(self, symbol: str) -> float:
        return abs(self.positions.get(symbol, 0.0))

    def check_risk(self, symbol: str, side: str, size_usd: float) -> bool:
        new_pos = self.positions.get(symbol, 0.0)
        new_pos += size_usd if side == "buy" else -size_usd
        if abs(new_pos) > MAX_GROSS_USD:
            return False
        if self.daily_pnl <= -MAX_DAILY_LOSS:
            return False
        return True

_risk = RiskManager()

def check_risk(order: dict) -> bool:
    return _risk.check_risk(order["symbol"], order["side"], order["size_usd"])

def update_position(symbol: str, delta_usd: float):
    _risk.update_position(symbol, delta_usd)

def add_pnl(amount: float):
    _risk.add_pnl(amount)

def gross(symbol: str) -> float:
    return _risk.gross(symbol)

def daily_pnl() -> float:
    return _risk.daily_pnl
