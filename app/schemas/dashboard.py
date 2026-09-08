from datetime import datetime

from pydantic import BaseModel


class MarketIndicator(BaseModel):
    symbol: str
    name: str
    value: float
    display_value: str
    change_percent: float | None
    provider: str = "mock"
    as_of: str | None = None


class MarketSession(BaseModel):
    market: str
    label: str
    status: str


class HoldingImpact(BaseModel):
    symbol: str
    name: str
    weight_percent: float
    change_percent: float
    importance: str
    color: str
    market_group: str
    currency: str | None = None
    quantity: float | None = None
    current_price: float | None = None
    average_purchase_price: float | None = None
    profit_loss_percent: float | None = None


class FocusItem(BaseModel):
    title: str
    description: str
    detail_summary: str
    evidence: list[str]
    related_symbols: list[str]


class DashboardSnapshot(BaseModel):
    generated_at: datetime
    sample_data: bool
    summary: str
    expected_portfolio_impact_percent: float | None
    portfolio_source: str = "demo"
    portfolio_status: str = "demo"
    portfolio_account_name: str | None = None
    portfolio_message: str = "샘플 포트폴리오입니다."
    portfolio_actual_available: bool = False
    market_sessions: list[MarketSession]
    markets: list[MarketIndicator]
    holdings: list[HoldingImpact]
    focus_items: list[FocusItem]
