from functools import lru_cache

from app.core.config import get_settings
from app.integrations.toss_invest import TossInvestClient
from app.schemas.broker import BrokerAccount, MarketQuote
from app.services.market_data import get_mock_quote


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
