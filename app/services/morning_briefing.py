import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import NewsArticle
from app.integrations.economic_data import EconomicMetric, get_cached_economic_metrics
from app.schemas.broker import BrokerHolding, BrokerPortfolio, MarketQuote
from app.schemas.dashboard import DashboardSnapshot, FocusItem, HoldingImpact, MarketIndicator
from app.services.broker import (
    get_broker_portfolio,
    get_market_indicator_quotes,
    get_market_quotes,
    get_usd_krw_metric,
)
from app.services.market_data import get_dashboard_snapshot

SEMICONDUCTOR_SYMBOLS = ["NVDA", "AMD", "005930", "000660"]
HOLDING_COLORS = ("blue", "purple", "slate")


def _format_quote(quote: MarketQuote) -> str:
    change = quote.change_percent
    change_text = "등락률 확인 불가" if change is None else f"{change:+.2f}%"
    price = (
        f"₩{quote.current_price:,.0f}"
        if quote.currency == "KRW"
        else f"${quote.current_price:,.2f}"
    )
    return f"{quote.symbol} {price} ({change_text})"


def _recent_focus_news(
    news: list[NewsArticle],
    now: datetime | None = None,
) -> list[NewsArticle]:
    reference_time = now or datetime.now(UTC)
    lookback_hours = 72 if reference_time.weekday() == 0 else 36
    cutoff = reference_time - timedelta(hours=lookback_hours)
    recent = []
    for article in news:
        published_at = article.published_at
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        if published_at >= cutoff:
            recent.append(article)
    return recent


def _news_reason(
    news: list[NewsArticle],
    category: str,
    relevance_keywords: tuple[str, ...] = (),
    fallback_keywords: tuple[str, ...] = (),
) -> str:
    def relevance_score(item: NewsArticle, keywords: tuple[str, ...]) -> int:
        text = f"{item.title} {item.korean_summary or ''}".lower()
        return sum(text.count(keyword.lower()) for keyword in keywords)

    candidates = [item for item in news if item.category == category and item.korean_summary]
    article = (
        max(candidates, key=lambda item: relevance_score(item, relevance_keywords))
        if candidates
        else None
    )
    if article is None and fallback_keywords:
        fallback_candidates = [
            item
            for item in news
            if item.korean_summary
            and any(keyword in item.korean_summary for keyword in fallback_keywords)
        ]
        article = (
            max(
                fallback_candidates,
                key=lambda item: relevance_score(item, fallback_keywords),
            )
            if fallback_candidates
            else None
        )
    if article is None:
        return "선정 시간 범위 내 관련 뉴스가 없어 변동 원인을 단정할 수 없습니다."
    return f"{article.source}: {article.korean_summary}"


def _metric_direction(metric: EconomicMetric) -> str:
    direction = "상승" if metric.value > metric.previous_value else "하락"
    return direction


def _to_market_indicator(
    symbol: str,
    name: str,
    metric: EconomicMetric,
    provider: str,
) -> MarketIndicator:
    return MarketIndicator(
        symbol=symbol,
        name=name,
        value=metric.value,
        display_value=f"{metric.value:,.2f}",
        change_percent=metric.change_percent,
        provider=provider,
        as_of=metric.as_of,
    )


def _build_holding_impacts(holdings: list[BrokerHolding]) -> list[HoldingImpact]:
    market_totals: dict[str, float] = {}
    for holding in holdings:
        market_totals[holding.market_country] = (
            market_totals.get(holding.market_country, 0) + holding.market_value
        )

    impacts = []
    for holding in holdings:
        total = market_totals[holding.market_country]
        weight = round(holding.market_value / total * 100, 1) if total else 0
        importance = "high" if weight >= 30 else "medium" if weight >= 15 else "low"
        color_index = sum(ord(character) for character in holding.symbol) % len(HOLDING_COLORS)
        impacts.append(
            HoldingImpact(
                symbol=holding.symbol,
                name=holding.name,
                weight_percent=weight,
                change_percent=round(holding.daily_profit_loss_percent, 2),
                importance=importance,
                color=HOLDING_COLORS[color_index],
                market_group=holding.market_country,
                currency=holding.currency,
                quantity=holding.quantity,
                current_price=holding.current_price,
                average_purchase_price=holding.average_purchase_price,
                profit_loss_percent=round(holding.profit_loss_percent, 2),
            )
        )
    return impacts


def _build_dynamic_focus_items(
    news: list[NewsArticle],
    semiconductor_quotes: dict[str, MarketQuote],
    metrics: dict[str, EconomicMetric],
    markets: list[MarketIndicator],
) -> list[FocusItem]:
    candidates: list[tuple[float, FocusItem]] = []
    news_counts: dict[str, int] = {}
    for article in news:
        if article.korean_summary:
            news_counts[article.category] = news_counts.get(article.category, 0) + 1

    def news_boost(category: str) -> float:
        return min(news_counts.get(category, 0), 3) * 0.15

    quote_evidence = [_format_quote(quote) for quote in semiconductor_quotes.values()]
    quote_changes = [
        quote.change_percent
        for quote in semiconductor_quotes.values()
        if quote.change_percent is not None
    ]
    if quote_changes:
        average_change = sum(quote_changes) / len(quote_changes)
        direction = "강세" if average_change >= 0 else "약세"
        candidates.append(
            (
                abs(average_change) + news_boost("반도체"),
                FocusItem(
                    title=f"반도체 업종 {direction} 지속 여부",
                    description=(
                        f"관련 {len(quote_changes)}종목 평균 {average_change:+.2f}%"
                    ),
                    detail_summary=_news_reason(
                        news,
                        "반도체",
                        ("반도체", "semiconductor", "chip", "메모리", "dram", "nand"),
                    ),
                    evidence=quote_evidence,
                    related_symbols=list(semiconductor_quotes),
                ),
            )
        )

    market_by_symbol = {item.symbol: item for item in markets}
    for symbols, market_name, keywords in (
        (("IXIC", "SPX"), "미국 증시", ("미국 증시", "나스닥", "s&p", "기술주")),
        (("KOSPI", "KOSDAQ"), "국내 증시", ("국내 증시", "코스피", "코스닥", "외국인")),
    ):
        available = [
            market_by_symbol[symbol]
            for symbol in symbols
            if symbol in market_by_symbol
            and market_by_symbol[symbol].change_percent is not None
        ]
        if available:
            leading = max(available, key=lambda item: abs(item.change_percent or 0))
            direction = "상승" if (leading.change_percent or 0) >= 0 else "하락"
            evidence = [
                f"{item.name} {item.display_value} ({item.change_percent:+.2f}%), "
                f"기준일 {item.as_of or '확인 불가'}"
                for item in available
                if item.change_percent is not None
            ]
            candidates.append(
                (
                    abs(leading.change_percent or 0),
                    FocusItem(
                        title=f"{market_name} {direction} 흐름",
                        description=(
                            f"{leading.name} {leading.change_percent:+.2f}% · "
                            f"{leading.display_value}"
                        ),
                        detail_summary=_news_reason(
                            news,
                            "시장",
                            fallback_keywords=keywords,
                        ),
                        evidence=evidence,
                        related_symbols=list(symbols),
                    ),
                )
            )

    treasury = metrics.get("treasury")
    if treasury:
        change_bps = (treasury.value - treasury.previous_value) * 100
        candidates.append(
            (
                abs(change_bps) / 5 + news_boost("금리"),
                FocusItem(
                    title="미국 장기 국채 금리",
                    description=(
                        f"미국 10년물 {treasury.value:.2f}% · 전일 대비 {change_bps:+.1f}bp"
                    ),
                    detail_summary=_news_reason(
                        news,
                        "금리",
                        (
                            f"국채 금리가 {_metric_direction(treasury)}",
                            f"채권 금리가 {_metric_direction(treasury)}",
                            "10년물",
                            "treasury",
                            "yield",
                        ),
                    ),
                    evidence=[
                        f"10년물 금리 {treasury.previous_value:.2f}% → "
                        f"{treasury.value:.2f}% ({_metric_direction(treasury)}), "
                        f"기준일 {treasury.as_of}"
                    ],
                    related_symbols=["US10Y", "IXIC"],
                ),
            )
        )

    usdkrw = metrics.get("usdkrw")
    if usdkrw:
        candidates.append(
            (
                abs(usdkrw.change_percent) + news_boost("환율"),
                FocusItem(
                    title="원·달러 환율",
                    description=(
                        f"USD/KRW {usdkrw.value:,.2f}원 · {usdkrw.change_percent:+.2f}%"
                    ),
                    detail_summary=_news_reason(
                        news,
                        "환율",
                        fallback_keywords=("강달러", "약달러", "달러화", "원화", "환율"),
                    ),
                    evidence=[
                        f"USD/KRW {usdkrw.previous_value:,.2f}원 → "
                        f"{usdkrw.value:,.2f}원 ({_metric_direction(usdkrw)}), "
                        f"기준일 {usdkrw.as_of}"
                    ],
                    related_symbols=["USDKRW", "KOSPI", "KOSDAQ"],
                ),
            )
        )

    for category, title in (
        ("전쟁·지정학", "전쟁·지정학 주요 이슈"),
        ("실적", "기업 실적 주요 이슈"),
    ):
        category_articles = [
            article
            for article in news
            if article.category == category and article.korean_summary
        ]
        if category_articles:
            related_symbols = list(
                dict.fromkeys(
                    symbol
                    for article in category_articles
                    for symbol in article.symbols
                )
            )[:6]
            candidates.append(
                (
                    0.35 + min(len(category_articles), 3) * 0.2,
                    FocusItem(
                        title=title,
                        description=f"관련 주요 뉴스 {len(category_articles)}건 확인",
                        detail_summary=_news_reason(news, category),
                        evidence=[
                            f"{article.source}: {article.title}"
                            for article in category_articles[:3]
                        ],
                        related_symbols=related_symbols,
                    ),
                )
            )

    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    return [item for _, item in candidates[:3]]


async def build_dashboard_snapshot(
    session: AsyncSession,
    demo_portfolio: bool = False,
) -> DashboardSnapshot:
    snapshot = get_dashboard_snapshot()
    news = list(
        await session.scalars(
            select(NewsArticle)
            .where(NewsArticle.provider == get_settings().news_provider)
            .order_by(NewsArticle.published_at.desc())
            .limit(200)
        )
    )

    settings = get_settings()
    alpha_key = (
        settings.alpha_vantage_api_key.get_secret_value()
        if settings.alpha_vantage_api_key
        else None
    )
    external_results = await asyncio.gather(
        get_market_quotes(SEMICONDUCTOR_SYMBOLS),
        get_cached_economic_metrics(alpha_key)
        if settings.market_data_provider == "toss"
        else asyncio.sleep(0, result={}),
        get_usd_krw_metric(),
        get_market_indicator_quotes(["KOSPI", "KOSDAQ"]),
        get_broker_portfolio()
        if settings.market_data_provider == "toss" and not demo_portfolio
        else asyncio.sleep(0, result=None),
        return_exceptions=True,
    )
    semiconductor_quotes = (
        external_results[0] if isinstance(external_results[0], dict) else {}
    )
    metrics: dict[str, EconomicMetric] = (
        external_results[1] if isinstance(external_results[1], dict) else {}
    )
    toss_usdkrw = (
        external_results[2] if isinstance(external_results[2], EconomicMetric) else None
    )
    toss_indices = external_results[3] if isinstance(external_results[3], dict) else {}
    portfolio = (
        external_results[4] if isinstance(external_results[4], BrokerPortfolio) else None
    )
    if toss_usdkrw:
        metrics["usdkrw"] = toss_usdkrw

    market_updates: dict[str, MarketIndicator] = {}
    for key, symbol, name in (
        ("nasdaq", "IXIC", "NASDAQ Composite"),
        ("sp500", "SPX", "S&P 500"),
        ("usdkrw", "USDKRW", "USD / KRW"),
    ):
        metric = metrics.get(key)
        if metric:
            market_updates[symbol] = _to_market_indicator(
                symbol,
                name,
                metric,
                "toss" if key == "usdkrw" else "fred",
            )
    for symbol, quote in toss_indices.items():
        market_updates[symbol] = MarketIndicator(
            symbol=symbol,
            name=symbol,
            value=quote.current_value,
            display_value=f"{quote.current_value:,.2f}",
            change_percent=quote.change_percent,
            provider="toss",
            as_of=quote.timestamp,
        )
    markets = [market_updates.get(item.symbol, item) for item in snapshot.markets]
    actual_market_changes = [
        f"{item.name} {item.change_percent:+.2f}%"
        for item in markets
        if item.provider != "mock" and item.change_percent is not None
    ]
    market_summary = (
        " · ".join(actual_market_changes)
        if actual_market_changes
        else snapshot.summary
    )

    focus_items = _build_dynamic_focus_items(
        _recent_focus_news(news),
        semiconductor_quotes,
        metrics,
        markets,
    )

    portfolio_updates: dict[str, object]
    if settings.market_data_provider != "toss" or demo_portfolio:
        portfolio_updates = {
            "sample_data": True,
            "portfolio_source": "demo",
            "portfolio_status": "demo",
            "portfolio_account_name": None,
            "portfolio_message": "기능 확인을 위한 데모 포트폴리오입니다.",
            "portfolio_actual_available": settings.market_data_provider == "toss",
        }
    elif portfolio is None:
        portfolio_updates = {
            "sample_data": False,
            "expected_portfolio_impact_percent": None,
            "portfolio_source": "toss",
            "portfolio_status": "unavailable",
            "portfolio_account_name": None,
            "portfolio_message": "토스증권 포트폴리오를 불러오지 못했습니다.",
            "portfolio_actual_available": True,
            "holdings": [],
        }
    elif portfolio.status == "no_account":
        portfolio_updates = {
            "sample_data": False,
            "expected_portfolio_impact_percent": None,
            "portfolio_source": "toss",
            "portfolio_status": "no_account",
            "portfolio_account_name": None,
            "portfolio_message": "조회할 수 있는 토스증권 계좌가 없습니다.",
            "portfolio_actual_available": True,
            "holdings": [],
        }
    else:
        is_empty = portfolio.status == "empty"
        portfolio_updates = {
            "sample_data": False,
            "expected_portfolio_impact_percent": (
                0 if is_empty else portfolio.daily_profit_loss_percent
            ),
            "portfolio_source": "toss",
            "portfolio_status": portfolio.status,
            "portfolio_account_name": portfolio.account_name,
            "portfolio_message": (
                "토스증권 계좌는 연결됐지만 현재 보유 종목이 없습니다."
                if is_empty
                else "토스증권의 실제 보유 종목과 일일 손익 기준입니다."
            ),
            "portfolio_actual_available": True,
            "holdings": _build_holding_impacts(portfolio.holdings),
        }
    return snapshot.model_copy(
        update={
            "summary": market_summary,
            "markets": markets,
            "focus_items": focus_items,
            **portfolio_updates,
        }
    )
