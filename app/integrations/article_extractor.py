import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import urljoin, urlsplit

import httpx
from trafilatura import extract

MAX_DOWNLOAD_BYTES = 1_500_000
MAX_CONTENT_CHARS = 20_000
MIN_CONTENT_CHARS = 300
MAX_REDIRECTS = 3


@dataclass(frozen=True)
class ExtractionResult:
    status: str
    text: str | None = None
    content_hash: str | None = None


class ArticleExtractor:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        enforce_public_network: bool = True,
    ) -> None:
        self._transport = transport
        self._enforce_public_network = enforce_public_network

    async def extract(self, source_url: str) -> ExtractionResult:
        current_url = source_url
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10, connect=5),
            transport=self._transport,
            follow_redirects=False,
            headers={"User-Agent": "MorningBell/0.1 news summarizer"},
        ) as client:
            for _ in range(MAX_REDIRECTS + 1):
                validation_error = await self._validate_url(current_url)
                if validation_error:
                    return ExtractionResult(validation_error)

                try:
                    async with client.stream("GET", current_url) as response:
                        if response.is_redirect:
                            location = response.headers.get("location")
                            if not location:
                                return ExtractionResult("http_error")
                            current_url = urljoin(current_url, location)
                            continue
                        if response.is_error:
                            return ExtractionResult("http_error")

                        content_type = response.headers.get("content-type", "").lower()
                        if (
                            "text/html" not in content_type
                            and "application/xhtml+xml" not in content_type
                        ):
                            return ExtractionResult("unsupported_content")

                        content_length = response.headers.get("content-length")
                        if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                            return ExtractionResult("too_large")

                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > MAX_DOWNLOAD_BYTES:
                                return ExtractionResult("too_large")
                except (httpx.HTTPError, ValueError):
                    return ExtractionResult("http_error")

                extracted = await asyncio.to_thread(
                    extract,
                    bytes(body),
                    url=current_url,
                    include_comments=False,
                    include_tables=False,
                    favor_precision=True,
                )
                if not extracted:
                    return ExtractionResult("extraction_failed")
                normalized = extracted.strip()
                if len(normalized) < MIN_CONTENT_CHARS:
                    return ExtractionResult("too_short")
                normalized = normalized[:MAX_CONTENT_CHARS]
                return ExtractionResult(
                    status="success",
                    text=normalized,
                    content_hash=sha256(normalized.encode()).hexdigest(),
                )

        return ExtractionResult("too_many_redirects")

    async def _validate_url(self, url: str) -> str | None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "invalid_url"
        if parsed.username or parsed.password:
            return "invalid_url"
        if parsed.port not in {None, 80, 443}:
            return "blocked_address"
        if not self._enforce_public_network:
            return None

        try:
            addresses = await asyncio.get_running_loop().getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror:
            return "dns_error"
        if not addresses:
            return "dns_error"
        if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            return "blocked_address"
        return None
