from pydantic import BaseModel


class BrokerAccount(BaseModel):
    account_seq: str
    name: str | None = None


class BrokerAccountList(BaseModel):
    provider: str
    accounts: list[BrokerAccount]


class MarketQuote(BaseModel):
    symbol: str
    current_price: float
    currency: str
    timestamp: str | None = None
    change_percent: float | None = None


class MarketIndicatorQuote(BaseModel):
    symbol: str
    current_value: float
    previous_value: float | None = None
    timestamp: str | None = None

    @property
    def change_percent(self) -> float | None:
        if self.previous_value in {None, 0}:
            return None
        return round(
            (self.current_value - self.previous_value) / self.previous_value * 100,
            2,
        )


class StockMetadata(BaseModel):
    symbol: str
    name: str
    market: str
    currency: str
