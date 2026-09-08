from typing import Literal

from pydantic import BaseModel, Field


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


class BrokerHolding(BaseModel):
    symbol: str
    name: str
    market_country: Literal["KR", "US"]
    currency: Literal["KRW", "USD"]
    quantity: float
    current_price: float
    average_purchase_price: float
    purchase_amount: float
    market_value: float
    profit_loss: float
    profit_loss_percent: float
    daily_profit_loss: float
    daily_profit_loss_percent: float


class BrokerPortfolio(BaseModel):
    provider: str
    status: Literal["ready", "empty", "no_account", "demo"]
    account_seq: str | None = None
    account_name: str | None = None
    daily_profit_loss_percent: float | None = None
    holdings: list[BrokerHolding] = Field(default_factory=list)
