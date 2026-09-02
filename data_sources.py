from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests


# ============================================================
# MARKET PRICE RESULT
# ============================================================

@dataclass
class MarketPrice:
    ticker: str
    price: Optional[float]
    currency: Optional[str]
    market_time: Optional[datetime]
    retrieved_at: datetime
    source: str
    source_url: str
    error: Optional[str] = None


# ============================================================
# YAHOO FINANCE PRICE RETRIEVAL
# ============================================================

def get_yahoo_price(ticker: str) -> MarketPrice:
    """
    Retrieve the latest directly reported Yahoo Finance market price.

    This does NOT reconstruct prices from percentage moves.

    The returned object includes:
    - price
    - market timestamp
    - retrieval timestamp
    - source
    - source URL
    """

    ticker = ticker.upper().strip()

    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{ticker}?interval=1d&range=5d"
    )

    retrieved_at = datetime.now(timezone.utc)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; ContrarianValueScreen/1.0)"
        )
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15,
        )

        response.raise_for_status()

        payload = response.json()

        chart = payload.get("chart", {})

        if chart.get("error"):
            return MarketPrice(
                ticker=ticker,
                price=None,
                currency=None,
                market_time=None,
                retrieved_at=retrieved_at,
                source="Yahoo Finance",
                source_url=url,
                error=str(chart["error"]),
            )

        results = chart.get("result")

        if not results:
            return MarketPrice(
                ticker=ticker,
                price=None,
                currency=None,
                market_time=None,
                retrieved_at=retrieved_at,
                source="Yahoo Finance",
                source_url=url,
                error="No price result returned.",
            )

        result = results[0]

        meta = result.get("meta", {})

        price = meta.get("regularMarketPrice")
        currency = meta.get("currency")
        market_timestamp = meta.get(
            "regularMarketTime"
        )

        market_time = None

        if market_timestamp:
            market_time = datetime.fromtimestamp(
                market_timestamp,
                tz=timezone.utc,
            )

        if price is None:
            return MarketPrice(
                ticker=ticker,
                price=None,
                currency=currency,
                market_time=market_time,
                retrieved_at=retrieved_at,
                source="Yahoo Finance",
                source_url=url,
                error=(
                    "Yahoo Finance did not return "
                    "regularMarketPrice."
                ),
            )

        return MarketPrice(
            ticker=ticker,
            price=float(price),
            currency=currency,
            market_time=market_time,
            retrieved_at=retrieved_at,
            source="Yahoo Finance",
            source_url=url,
            error=None,
        )

    except Exception as exc:

        return MarketPrice(
            ticker=ticker,
            price=None,
            currency=None,
            market_time=None,
            retrieved_at=retrieved_at,
            source="Yahoo Finance",
            source_url=url,
            error=str(exc),
        )
