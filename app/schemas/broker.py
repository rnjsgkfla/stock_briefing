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
