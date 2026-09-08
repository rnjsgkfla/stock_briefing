from datetime import datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.integrations.economic_data import EconomicMetric
from app.integrations.toss_invest import TossInvestClient
from app.schemas.broker import (
    BrokerAccount,
    BrokerPortfolio,
    MarketIndicatorQuote,
    MarketQuote,
    StockMetadata,
)
from app.services.market_data import STOCK_CATALOG, get_mock_quote


@lru_cache
def get_toss_invest_client() -> TossInvestClient:
    settings = get_settings()
    client_id = settings.toss_invest_client_id
    client_secret = settings.toss_invest_client_secret
    if client_id is None or not client_id.get_secret_value():
        raise RuntimeError("TOSS_INVEST_CLIENT_ID가 필요합니다.")
    if client_secret is None or not client_secret.get_secret_value():
        raise RuntimeError("TOSS_INVEST_CLIENT_SECRET이 필요합니다.")

    return TossInvestClient(
        base_url=settings.toss_invest_base_url,
        client_id=client_id.get_secret_value(),
        client_secret=client_secret.get_secret_value(),
    )


async def get_broker_accounts() -> list[BrokerAccount]:
    settings = get_settings()
    if settings.market_data_provider != "toss":
        return []
    return await get_toss_invest_client().get_accounts()


async def get_broker_portfolio(account_seq: str | None = None) -> BrokerPortfolio:
    settings = get_settings()
    if settings.market_data_provider != "toss":
        return BrokerPortfolio(provider="mock", status="demo")

    client = get_toss_invest_client()
    accounts = await client.get_accounts()
    if not accounts:
        return BrokerPortfolio(provider="toss", status="no_account")

    selected_seq = account_seq or settings.toss_invest_account or accounts[0].account_seq
    account = next((item for item in accounts if item.account_seq == selected_seq), None)
    if account is None:
        raise RuntimeError("설정한 토스증권 계좌를 계좌 목록에서 찾을 수 없습니다.")

    portfolio = await client.get_holdings(account.account_seq)
    return portfolio.model_copy(update={"account_name": account.name})


async def get_market_quotes(symbols: list[str]) -> dict[str, MarketQuote]:
    settings = get_settings()
    if settings.market_data_provider == "toss":
        return await get_toss_invest_client().get_prices(symbols)

    quotes = {}
    for symbol in symbols:
        price, change_percent, _ = get_mock_quote(symbol)
        quotes[symbol] = MarketQuote(
            symbol=symbol,
            current_price=price,
            currency="KRW" if symbol.isdigit() else "USD",
            change_percent=change_percent,
        )
    return quotes


async def get_stock_metadata(symbol: str) -> StockMetadata | None:
    settings = get_settings()
    if settings.market_data_provider == "toss":
        return await get_toss_invest_client().get_stock(symbol)

    metadata = STOCK_CATALOG.get(symbol)
    if metadata is None:
        return None
    return StockMetadata(symbol=symbol, **metadata)


async def get_market_indicator_quotes(
    symbols: list[str],
) -> dict[str, MarketIndicatorQuote]:
    settings = get_settings()
    if settings.market_data_provider != "toss":
        return {}
    return await get_toss_invest_client().get_market_indicators(symbols)


async def get_usd_krw_metric() -> EconomicMetric | None:
    settings = get_settings()
    if settings.market_data_provider != "toss":
        return None

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    days_back = 3 if now.weekday() == 0 else 1
    previous_time = (now - timedelta(days=days_back)).isoformat()
    client = get_toss_invest_client()
    current, current_as_of = await client.get_exchange_rate()
    previous, _ = await client.get_exchange_rate(previous_time)
    return EconomicMetric(value=current, previous_value=previous, as_of=current_as_of)
