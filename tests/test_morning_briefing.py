from datetime import UTC, datetime, timedelta

from app.db.models import NewsArticle
from app.integrations.economic_data import EconomicMetric
from app.schemas.broker import BrokerHolding, MarketQuote
from app.schemas.dashboard import MarketIndicator
from app.services.morning_briefing import (
    _build_dynamic_focus_items,
    _build_holding_impacts,
    _news_reason,
    _recent_focus_news,
)


def _article(title: str, summary: str, category: str = "금리") -> NewsArticle:
    return NewsArticle(
        external_id=title,
        title=title,
        summary=summary,
        korean_summary=summary,
        category=category,
        source="테스트 뉴스",
        source_url="https://example.com/news",
        published_at=datetime.now(UTC),
        symbols=[],
        sentiment=None,
        provider="alpha_vantage",
    )


def test_news_reason_prefers_article_relevant_to_the_metric() -> None:
    unrelated = _article(
        "비트코인 ETF 자금 유입",
        "연준 관계자의 금리 발언이 시장에 영향을 미쳤습니다.",
    )
    relevant = _article(
        "미국 채권시장 동향",
        "경제 활동과 재정 적자 우려로 미국 채권 금리가 상승했습니다.",
    )

    result = _news_reason(
        [unrelated, relevant],
        "금리",
        ("국채 금리", "채권 금리", "10년물", "treasury", "yield"),
    )

    assert "채권 금리가 상승" in result


def test_news_reason_uses_keyword_fallback_when_category_is_missing() -> None:
    article = _article(
        "금 가격 하락",
        "강달러와 연준의 금리 전망이 금 가격에 영향을 미쳤습니다.",
        category="기업",
    )

    result = _news_reason(
        [article],
        "환율",
        fallback_keywords=("강달러", "약달러", "달러화", "원화", "환율"),
    )

    assert "강달러" in result


def test_holding_impacts_use_weight_within_each_market() -> None:
    holdings = [
        BrokerHolding(
            symbol="005930",
            name="삼성전자",
            market_country="KR",
            currency="KRW",
            quantity=10,
            current_price=70000,
            average_purchase_price=65000,
            purchase_amount=650000,
            market_value=700000,
            profit_loss=50000,
            profit_loss_percent=7.69,
            daily_profit_loss=14000,
            daily_profit_loss_percent=2,
        ),
        BrokerHolding(
            symbol="000660",
            name="SK하이닉스",
            market_country="KR",
            currency="KRW",
            quantity=1,
            current_price=300000,
            average_purchase_price=290000,
            purchase_amount=290000,
            market_value=300000,
            profit_loss=10000,
            profit_loss_percent=3.45,
            daily_profit_loss=-3000,
            daily_profit_loss_percent=-1,
        ),
    ]

    impacts = _build_holding_impacts(holdings)

    assert impacts[0].weight_percent == 70
    assert impacts[1].weight_percent == 30
    assert impacts[0].current_price == 70000
    assert impacts[1].change_percent == -1


def test_dynamic_focus_selects_strongest_market_and_news_signals() -> None:
    news = [
        _article(
            f"지정학 뉴스 {index}",
            "국제 분쟁과 제재가 금융시장 변동성을 높였습니다.",
            category="전쟁·지정학",
        )
        for index in range(3)
    ]
    quotes = {
        "NVDA": MarketQuote(
            symbol="NVDA",
            current_price=200,
            currency="USD",
            change_percent=0.2,
        )
    }
    markets = [
        MarketIndicator(
            symbol="IXIC",
            name="NASDAQ Composite",
            value=20000,
            display_value="20,000.00",
            change_percent=0.4,
            provider="fred",
            as_of="2026-09-08",
        ),
        MarketIndicator(
            symbol="KOSPI",
            name="KOSPI",
            value=3000,
            display_value="3,000.00",
            change_percent=-2.5,
            provider="toss",
            as_of="2026-09-09",
        ),
    ]
    metrics = {
        "treasury": EconomicMetric(value=4.001, previous_value=4, as_of="2026-09-08"),
        "usdkrw": EconomicMetric(value=1351, previous_value=1350, as_of="2026-09-09"),
    }

    result = _build_dynamic_focus_items(news, quotes, metrics, markets)

    assert len(result) == 3
    assert result[0].title == "국내 증시 하락 흐름"
    assert result[0].description == "KOSPI -2.50% · 3,000.00"
    assert result[1].title == "전쟁·지정학 주요 이슈"
    assert result[2].title == "미국 증시 상승 흐름"


def test_recent_focus_news_uses_longer_monday_window() -> None:
    monday = datetime(2026, 9, 7, 0, tzinfo=UTC)
    weekend_article = _article("주말 뉴스", "주말 사이 발생한 주요 이슈입니다.")
    weekend_article.published_at = monday - timedelta(hours=60)
    stale_article = _article("오래된 뉴스", "지난주에 발생한 이슈입니다.")
    stale_article.published_at = monday - timedelta(hours=80)

    result = _recent_focus_news([weekend_article, stale_article], now=monday)

    assert result == [weekend_article]
