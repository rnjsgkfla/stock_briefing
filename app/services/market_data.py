from datetime import UTC, datetime

from app.schemas.dashboard import DashboardSnapshot, FocusItem, HoldingImpact, MarketIndicator

STOCK_CATALOG: dict[str, dict[str, str]] = {
    "NVDA": {"name": "NVIDIA", "market": "NASDAQ", "currency": "USD"},
    "AAPL": {"name": "Apple", "market": "NASDAQ", "currency": "USD"},
    "MSFT": {"name": "Microsoft", "market": "NASDAQ", "currency": "USD"},
    "TSLA": {"name": "Tesla", "market": "NASDAQ", "currency": "USD"},
    "AMD": {"name": "Advanced Micro Devices", "market": "NASDAQ", "currency": "USD"},
    "GOOGL": {"name": "Alphabet", "market": "NASDAQ", "currency": "USD"},
    "AMZN": {"name": "Amazon", "market": "NASDAQ", "currency": "USD"},
    "META": {"name": "Meta Platforms", "market": "NASDAQ", "currency": "USD"},
}

MOCK_QUOTES: dict[str, tuple[float, float, int]] = {
    "NVDA": (179.42, 2.18, 6),
    "AAPL": (238.17, 0.41, 3),
    "MSFT": (507.33, -0.12, 2),
    "TSLA": (347.21, -1.08, 4),
    "AMD": (168.93, 1.76, 2),
    "GOOGL": (214.55, 0.73, 2),
    "AMZN": (231.26, 0.38, 1),
    "META": (764.81, 1.02, 3),
}


def get_mock_quote(symbol: str) -> tuple[float, float, int]:
    return MOCK_QUOTES[symbol]


def get_dashboard_snapshot() -> DashboardSnapshot:
    return DashboardSnapshot(
        generated_at=datetime.now(UTC),
        sample_data=True,
        summary=(
            "기술주 중심의 반등이 나타났지만 금리 불확실성은 남아 있습니다. "
            "오늘은 반도체 종목의 변동성을 먼저 확인하세요."
        ),
        expected_portfolio_impact_percent=0.84,
        markets=[
            MarketIndicator(
                symbol="IXIC",
                name="NASDAQ",
                value=18847.28,
                display_value="18,847.28",
                change_percent=1.24,
            ),
            MarketIndicator(
                symbol="SPX",
                name="S&P 500",
                value=6481.42,
                display_value="6,481.42",
                change_percent=0.62,
            ),
            MarketIndicator(
                symbol="USDKRW",
                name="USD / KRW",
                value=1387.2,
                display_value="1,387.20",
                change_percent=-0.31,
            ),
        ],
        holdings=[
            HoldingImpact(
                symbol="NVDA",
                name="엔비디아",
                weight_percent=38,
                change_percent=2.18,
                importance="high",
                color="purple",
            ),
            HoldingImpact(
                symbol="AAPL",
                name="애플",
                weight_percent=27,
                change_percent=0.41,
                importance="medium",
                color="slate",
            ),
            HoldingImpact(
                symbol="MSFT",
                name="마이크로소프트",
                weight_percent=21,
                change_percent=-0.12,
                importance="low",
                color="blue",
            ),
        ],
        focus_items=[
            FocusItem(
                title="반도체 업종 반등 지속 여부",
                description="엔비디아 비중이 높아 장 초반 움직임을 우선 확인하세요.",
            ),
            FocusItem(
                title="미국 장기 국채 금리",
                description="금리 재상승 시 성장주 변동성이 확대될 수 있습니다.",
            ),
            FocusItem(
                title="원·달러 환율",
                description="해외 주식 원화 평가액에 미치는 영향을 확인하세요.",
            ),
        ],
    )
