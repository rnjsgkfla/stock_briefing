from datetime import datetime

from pydantic import BaseModel


class MarketIndicator(BaseModel):
    symbol: str
    name: str
    value: float
    display_value: str
    change_percent: float


class HoldingImpact(BaseModel):
    symbol: str
    name: str
    weight_percent: float
    change_percent: float
    importance: str
    color: str


class FocusItem(BaseModel):
    title: str
    description: str


class DashboardSnapshot(BaseModel):
    generated_at: datetime
    sample_data: bool
    summary: str
    expected_portfolio_impact_percent: float
    markets: list[MarketIndicator]
    holdings: list[HoldingImpact]
    focus_items: list[FocusItem]
