from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import NewsArticle
from app.integrations.economic_data import EconomicMetric, get_cached_economic_metrics
from app.schemas.broker import MarketQuote
from app.schemas.dashboard import DashboardSnapshot, FocusItem
from app.services.broker import get_market_quotes, get_usd_krw_metric
from app.services.market_data import get_dashboard_snapshot

SEMICONDUCTOR_SYMBOLS = ["NVDA", "AMD", "005930", "000660"]


def _format_quote(quote: MarketQuote) -> str:
    change = quote.change_percent
    change_text = "등락률 확인 불가" if change is None else f"{change:+.2f}%"
    price = (
        f"₩{quote.current_price:,.0f}"
        if quote.currency == "KRW"
        else f"${quote.current_price:,.2f}"
    )
    return f"{quote.symbol} {price} ({change_text})"


def _news_reason(
    news: list[NewsArticle],
    category: str,
    fallback_keywords: tuple[str, ...] = (),
) -> str:
    article = next(
        (
            item
            for item in news
            if item.category == category and item.korean_summary
        ),
        None,
    )
    if article is None and fallback_keywords:
        article = next(
            (
                item
                for item in news
                if item.korean_summary
                and any(keyword in item.korean_summary for keyword in fallback_keywords)
            ),
            None,
        )
    if article is None:
        return "관련 실제 뉴스의 한국어 요약이 아직 없습니다."
    return f"{article.source}: {article.korean_summary}"


def _metric_change(metric: EconomicMetric) -> str:
    direction = "상승" if metric.value > metric.previous_value else "하락"
    return f"{metric.previous_value:,.2f} → {metric.value:,.2f} ({direction})"


async def build_dashboard_snapshot(session: AsyncSession) -> DashboardSnapshot:
    snapshot = get_dashboard_snapshot()
    news = list(
        await session.scalars(
            select(NewsArticle)
            .where(NewsArticle.provider == get_settings().news_provider)
            .order_by(NewsArticle.published_at.desc())
            .limit(50)
        )
    )

    try:
        semiconductor_quotes = await get_market_quotes(SEMICONDUCTOR_SYMBOLS)
    except (RuntimeError, ValueError):
        semiconductor_quotes = {}

    settings = get_settings()
    metrics: dict[str, EconomicMetric] = {}
    if settings.news_provider == "alpha_vantage" and settings.alpha_vantage_api_key:
        metrics = await get_cached_economic_metrics(
            settings.alpha_vantage_api_key.get_secret_value()
        )
    try:
        toss_usdkrw = await get_usd_krw_metric()
    except RuntimeError:
        toss_usdkrw = None
    if toss_usdkrw:
        metrics["usdkrw"] = toss_usdkrw

    quote_evidence = [_format_quote(quote) for quote in semiconductor_quotes.values()]
    valid_changes = [
        quote.change_percent
        for quote in semiconductor_quotes.values()
        if quote.change_percent is not None
    ]
    average_change = sum(valid_changes) / len(valid_changes) if valid_changes else None
    semiconductor_description = (
        f"관련 종목 평균 등락률 {average_change:+.2f}%"
        if average_change is not None
        else "관련 종목 등락률 확인 불가"
    )

    treasury = metrics.get("treasury")
    treasury_change_bps = (
        (treasury.value - treasury.previous_value) * 100 if treasury else None
    )
    treasury_description = (
        f"미국 10년물 {treasury.value:.2f}% · 전일 대비 {treasury_change_bps:+.1f}bp"
        if treasury
        else "미국 10년물 금리 확인 불가"
    )
    usdkrw = metrics.get("usdkrw")
    usdkrw_description = (
        f"USD/KRW {usdkrw.value:,.2f}원 · {usdkrw.change_percent:+.2f}%"
        if usdkrw
        else "원·달러 환율 확인 불가"
    )

    focus_items = [
        FocusItem(
            title="반도체 업종 반등 지속 여부",
            description=semiconductor_description,
            detail_summary=_news_reason(news, "반도체"),
            evidence=quote_evidence or ["토스증권 시세를 불러오지 못했습니다."],
            related_symbols=list(semiconductor_quotes) or SEMICONDUCTOR_SYMBOLS,
        ),
        FocusItem(
            title="미국 장기 국채 금리",
            description=treasury_description,
            detail_summary=_news_reason(news, "금리"),
            evidence=(
                [f"10년물 금리 {_metric_change(treasury)}%, 기준일 {treasury.as_of}"]
                if treasury
                else ["경제지표 제공자에서 최신 금리를 받지 못했습니다."]
            ),
            related_symbols=["US10Y", "IXIC"],
        ),
        FocusItem(
            title="원·달러 환율",
            description=usdkrw_description,
            detail_summary=_news_reason(
                news,
                "환율",
                ("강달러", "약달러", "달러화", "원화", "환율"),
            ),
            evidence=(
                [f"USD/KRW {_metric_change(usdkrw)}원, 기준일 {usdkrw.as_of}"]
                if usdkrw
                else ["경제지표 제공자에서 최신 환율을 받지 못했습니다."]
            ),
            related_symbols=["USDKRW", "KOSPI", "KOSDAQ"],
        ),
    ]
    return snapshot.model_copy(update={"focus_items": focus_items})
