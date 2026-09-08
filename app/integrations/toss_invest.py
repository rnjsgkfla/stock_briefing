import asyncio
from collections.abc import Mapping
from time import monotonic
from typing import Any

import httpx

from app.schemas.broker import (
    BrokerAccount,
    BrokerHolding,
    BrokerPortfolio,
    MarketIndicatorQuote,
    MarketQuote,
    StockMetadata,
)


class TossInvestError(RuntimeError):
    pass


class TossInvestClient:
    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._transport = transport
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()

    async def _get_access_token(self) -> str:
        if self._access_token and monotonic() < self._token_expires_at:
            return self._access_token

        async with self._token_lock:
            if self._access_token and monotonic() < self._token_expires_at:
                return self._access_token

            payload = await self._send(
                "POST",
                "/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                authenticated=False,
            )
            token_payload = payload.get("result", payload)
            token = token_payload.get("access_token") or token_payload.get("accessToken")
            if not token:
                raise TossInvestError("토스증권 액세스 토큰이 응답에 없습니다.")

            expires_in = int(
                token_payload.get("expires_in") or token_payload.get("expiresIn") or 3600
            )
            self._access_token = str(token)
            self._token_expires_at = monotonic() + max(expires_in - 60, 1)
            return self._access_token

    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        data: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        request_headers = dict(headers or {})
        if authenticated:
            token = await self._get_access_token()
            request_headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=15,
                transport=self._transport,
            ) as client:
                response = await client.request(
                    method,
                    path,
                    params=params,
                    data=data,
                    headers=request_headers,
                )
        except httpx.HTTPError as exc:
            raise TossInvestError("토스증권 API에 연결하지 못했습니다.") from exc

        if response.is_error:
            message = "토스증권 API 요청에 실패했습니다."
            try:
                error = response.json().get("error", {})
                message = error.get("message") or message
            except ValueError:
                pass
            raise TossInvestError(f"{message} (HTTP {response.status_code})")

        try:
            return response.json()
        except ValueError as exc:
            raise TossInvestError("토스증권 API 응답이 JSON 형식이 아닙니다.") from exc

    async def get_accounts(self) -> list[BrokerAccount]:
        payload = await self._send("GET", "/api/v1/accounts")
        accounts = payload.get("result", [])
        if isinstance(accounts, dict):
            accounts = accounts.get("accounts", [])
        return [
            BrokerAccount(
                account_seq=str(account["accountSeq"]),
                name=account.get("name") or account.get("accountName"),
            )
            for account in accounts
            if account.get("accountSeq") is not None
        ]

    async def get_prices(self, symbols: list[str]) -> dict[str, MarketQuote]:
        if not symbols:
            return {}
        if len(symbols) > 200:
            raise ValueError("토스증권 현재가는 한 번에 최대 200종목까지 조회할 수 있습니다.")

        payload = await self._send(
            "GET",
            "/api/v1/prices",
            params={"symbols": ",".join(symbols)},
        )
        quotes = {}
        for item in payload.get("result", []):
            symbol = str(item["symbol"]).upper()
            quotes[symbol] = MarketQuote(
                symbol=symbol,
                current_price=float(item["lastPrice"]),
                currency=item["currency"],
                timestamp=item.get("timestamp"),
            )

        changes = await asyncio.gather(
            *(
                self._get_daily_change(symbol, quote.current_price)
                for symbol, quote in quotes.items()
            ),
            return_exceptions=True,
        )
        for symbol, change in zip(quotes, changes, strict=True):
            if not isinstance(change, Exception):
                quotes[symbol] = quotes[symbol].model_copy(update={"change_percent": change})
        return quotes

    async def get_holdings(self, account_seq: str) -> BrokerPortfolio:
        payload = await self._send(
            "GET",
            "/api/v1/holdings",
            headers={"X-Tossinvest-Account": account_seq},
        )
        result = payload.get("result", {})
        items = result.get("items", [])
        holdings = [
            BrokerHolding(
                symbol=str(item["symbol"]).upper(),
                name=str(item["name"]),
                market_country=item["marketCountry"],
                currency=item["currency"],
                quantity=float(item["quantity"]),
                current_price=float(item["lastPrice"]),
                average_purchase_price=float(item["averagePurchasePrice"]),
                purchase_amount=float(item["marketValue"]["purchaseAmount"]),
                market_value=float(item["marketValue"]["amount"]),
                profit_loss=float(item["profitLoss"]["amount"]),
                profit_loss_percent=float(item["profitLoss"]["rate"]) * 100,
                daily_profit_loss=float(item["dailyProfitLoss"]["amount"]),
                daily_profit_loss_percent=float(item["dailyProfitLoss"]["rate"]) * 100,
            )
            for item in items
        ]
        daily_rate = result.get("dailyProfitLoss", {}).get("rate")
        return BrokerPortfolio(
            provider="toss",
            status="ready" if holdings else "empty",
            account_seq=account_seq,
            daily_profit_loss_percent=(
                round(float(daily_rate) * 100, 2) if daily_rate is not None else None
            ),
            holdings=holdings,
        )

    async def get_stock(self, symbol: str) -> StockMetadata | None:
        payload = await self._send(
            "GET",
            "/api/v1/stocks",
            params={"symbols": symbol},
        )
        result = payload.get("result", [])
        if isinstance(result, dict):
            result = result.get("stocks", [result] if result.get("symbol") else [])
        if not result:
            return None

        item = result[0]
        return StockMetadata(
            symbol=str(item.get("symbol", symbol)).upper(),
            name=str(item.get("name") or item.get("stockName") or symbol),
            market=str(item.get("market") or item.get("exchange") or "UNKNOWN"),
            currency=str(item.get("currency") or ("KRW" if symbol.isdigit() else "USD")),
        )

    async def get_market_indicators(
        self,
        symbols: list[str],
    ) -> dict[str, MarketIndicatorQuote]:
        if not symbols:
            return {}
        payload = await self._send(
            "GET",
            "/api/v1/market-indicators/prices",
            params={"symbols": ",".join(symbols)},
        )
        items = payload.get("result", [])
        quotes = {
            str(item["symbol"]).upper(): MarketIndicatorQuote(
                symbol=str(item["symbol"]).upper(),
                current_value=float(item["lastPrice"]),
                timestamp=item.get("timestamp"),
            )
            for item in items
        }
        previous_values = await asyncio.gather(
            *(self._get_market_indicator_previous(symbol) for symbol in quotes),
            return_exceptions=True,
        )
        for symbol, result in zip(quotes, previous_values, strict=True):
            if isinstance(result, Exception):
                continue
            previous_value, timestamp = result
            quotes[symbol] = quotes[symbol].model_copy(
                update={
                    "previous_value": previous_value,
                    "timestamp": quotes[symbol].timestamp or timestamp,
                }
            )
        return quotes

    async def get_exchange_rate(self, date_time: str | None = None) -> tuple[float, str]:
        params = {"baseCurrency": "USD", "quoteCurrency": "KRW"}
        if date_time:
            params["dateTime"] = date_time
        payload = await self._send("GET", "/api/v1/exchange-rate", params=params)
        result = payload.get("result", {})
        rate = result.get("midRate") or result.get("rate")
        as_of = result.get("validFrom") or date_time
        if rate is None or as_of is None:
            raise TossInvestError("토스증권 원·달러 환율 값이 응답에 없습니다.")
        return float(rate), str(as_of)

    async def _get_daily_change(self, symbol: str, current_price: float) -> float | None:
        payload = await self._send(
            "GET",
            "/api/v1/candles",
            params={"symbol": symbol, "interval": "1d", "count": "2"},
        )
        candles = payload.get("result", {}).get("candles", [])
        if len(candles) < 2:
            return None
        previous_close = float(candles[1]["closePrice"])
        if previous_close == 0:
            return None
        return round((current_price - previous_close) / previous_close * 100, 2)

    async def _get_market_indicator_previous(self, symbol: str) -> tuple[float, str | None]:
        payload = await self._send(
            "GET",
            f"/api/v1/market-indicators/{symbol}/candles",
            params={"interval": "1d", "count": "2"},
        )
        candles = payload.get("result", {}).get("candles", [])
        if len(candles) < 2:
            raise TossInvestError(f"{symbol} 지수의 전일 종가가 없습니다.")
        return float(candles[1]["closePrice"]), candles[0].get("timestamp")
