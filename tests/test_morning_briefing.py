from datetime import UTC, datetime

from app.db.models import NewsArticle
from app.services.morning_briefing import _news_reason


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
