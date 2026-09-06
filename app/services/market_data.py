from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.schemas.dashboard import (
    DashboardSnapshot,
    FocusItem,
    HoldingImpact,
    MarketIndicator,
    MarketSession,
)

STOCK_CATALOG: dict[str, dict[str, str]] = {
    "NVDA": {"name": "NVIDIA", "market": "NASDAQ", "currency": "USD"},
    "AAPL": {"name": "Apple", "market": "NASDAQ", "currency": "USD"},
    "MSFT": {"name": "Microsoft", "market": "NASDAQ", "currency": "USD"},
    "TSLA": {"name": "Tesla", "market": "NASDAQ", "currency": "USD"},
    "AMD": {"name": "Advanced Micro Devices", "market": "NASDAQ", "currency": "USD"},
    "GOOGL": {"name": "Alphabet", "market": "NASDAQ", "currency": "USD"},
    "AMZN": {"name": "Amazon", "market": "NASDAQ", "currency": "USD"},
    "META": {"name": "Meta Platforms", "market": "NASDAQ", "currency": "USD"},
    "005930": {"name": "삼성전자", "market": "KOSPI", "currency": "KRW"},
    "000660": {"name": "SK하이닉스", "market": "KOSPI", "currency": "KRW"},
    "035420": {"name": "NAVER", "market": "KOSPI", "currency": "KRW"},
    "035720": {"name": "카카오", "market": "KOSPI", "currency": "KRW"},
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
    "005930": (72400, 1.26, 5),
    "000660": (208500, 2.41, 4),
    "035420": (226000, -0.44, 2),
    "035720": (42450, 0.71, 3),
}

STOCK_ALIASES = {
    "삼성전자": "005930",
    "SK하이닉스": "000660",
    "NAVER": "035420",
    "카카오": "035720",
}


def resolve_stock_symbol(value: str) -> str:
    return STOCK_ALIASES.get(value, value)


def get_mock_quote(symbol: str) -> tuple[float, float, int]:
    return MOCK_QUOTES[symbol]


def get_korean_market_status() -> str:
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    if now.weekday() >= 5:
        return "휴장"
    current_minutes = now.hour * 60 + now.minute
    if current_minutes < 9 * 60:
        return "개장 전"
    if current_minutes < 15 * 60 + 30:
        return "장중"
    return "마감"


def get_dashboard_snapshot() -> DashboardSnapshot:
    return DashboardSnapshot(
        generated_at=datetime.now(UTC),
        sample_data=True,
        summary=(
            "기술주 중심의 반등이 나타났지만 금리 불확실성은 남아 있습니다. "
            "오늘은 반도체 종목의 변동성을 먼저 확인하세요."
        ),
        expected_portfolio_impact_percent=0.84,
        market_sessions=[
            MarketSession(market="US", label="미국장", status="마감"),
            MarketSession(market="KR", label="국장", status=get_korean_market_status()),
        ],
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
            MarketIndicator(
                symbol="KOSPI",
                name="KOSPI",
                value=3210.01,
                display_value="3,210.01",
                change_percent=0.71,
            ),
            MarketIndicator(
                symbol="KOSDAQ",
                name="KOSDAQ",
                value=811.4,
                display_value="811.40",
                change_percent=-0.18,
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
                market_group="US",
            ),
            HoldingImpact(
                symbol="AAPL",
                name="애플",
                weight_percent=27,
                change_percent=0.41,
                importance="medium",
                color="slate",
                market_group="US",
            ),
            HoldingImpact(
                symbol="MSFT",
                name="마이크로소프트",
                weight_percent=21,
                change_percent=-0.12,
                importance="low",
                color="blue",
                market_group="US",
            ),
            HoldingImpact(
                symbol="005930",
                name="삼성전자",
                weight_percent=31,
                change_percent=1.26,
                importance="high",
                color="blue",
                market_group="KR",
            ),
            HoldingImpact(
                symbol="000660",
                name="SK하이닉스",
                weight_percent=24,
                change_percent=2.41,
                importance="high",
                color="purple",
                market_group="KR",
            ),
            HoldingImpact(
                symbol="035420",
                name="NAVER",
                weight_percent=18,
                change_percent=-0.44,
                importance="medium",
                color="slate",
                market_group="KR",
            ),
        ],
        focus_items=[
            FocusItem(
                title="반도체 업종 반등 지속 여부",
                description="엔비디아 비중이 높아 장 초반 움직임을 우선 확인하세요.",
                detail_summary=(
                    "미국 반도체주 강세가 국내 반도체 대형주의 투자심리에도 이어질 수 있습니다. "
                    "다만 개장 직후 추격보다 거래량과 외국인 수급을 함께 확인할 필요가 있습니다."
                ),
                evidence=[
                    "엔비디아 샘플 등락률 +2.18%, AMD +1.76%",
                    "관심 뉴스: 미국 기술주 강세와 반도체 업종 상승",
                    "국내 보유종목: 삼성전자·SK하이닉스",
                ],
                related_symbols=["NVDA", "AMD", "005930", "000660"],
            ),
            FocusItem(
                title="미국 장기 국채 금리",
                description="금리 재상승 시 성장주 변동성이 확대될 수 있습니다.",
                detail_summary=(
                    "장기 금리가 다시 오르면 미래 이익의 현재가치가 낮아져 성장주에 부담이 될 수 "
                    "있습니다. NASDAQ과 국내 인터넷 종목의 동반 움직임을 확인하세요."
                ),
                evidence=[
                    "NASDAQ 샘플 등락률 +1.24%",
                    "금리 민감 종목: TSLA·NAVER·카카오",
                    "뉴스에서 장기 금리 변동성 확대가 언급됨",
                ],
                related_symbols=["IXIC", "TSLA", "035420", "035720"],
            ),
            FocusItem(
                title="원·달러 환율",
                description="해외 주식 원화 평가액에 미치는 영향을 확인하세요.",
                detail_summary=(
                    "원화 강세는 미국 주식의 원화 환산 평가액을 낮출 수 있지만 외국인 국내주식 "
                    "수급에는 우호적으로 작용할 여지가 있습니다. 방향보다 변동 폭을 확인하세요."
                ),
                evidence=[
                    "USD/KRW 샘플 등락률 -0.31%",
                    "미국 주식 원화 환산 가치와 국내 외국인 수급에 동시 영향",
                    "KOSPI·KOSDAQ 개장 전 환율 변동 확인 필요",
                ],
                related_symbols=["USDKRW", "KOSPI", "KOSDAQ"],
            ),
        ],
    )
