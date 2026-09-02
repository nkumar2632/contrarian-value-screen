from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import io
import time

import pandas as pd
import requests

from eligibility import evaluate_eligibility


# ============================================================
# SETTINGS
# ============================================================

BATCH_SIZE = 25
REQUEST_TIMEOUT = 20
MAX_RETRIES = 4
BATCH_PAUSE_SECONDS = 0.8

MAX_FAILURE_RATE = 0.10


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class DiscoveredCandidate:
    ticker: str
    company: str
    entry_reason: str

    last_price: Optional[float]

    return_1d: Optional[float]
    return_1m: Optional[float]
    return_3m: Optional[float]
    return_6m: Optional[float]

    drawdown_from_52w_high: Optional[float]
    distance_from_52w_low: Optional[float]

    volume_ratio: Optional[float]
    discovery_score: Optional[float]

    eligibility_status: str
    eligibility_reason: str
    market_cap: Optional[float]
    profitable: Optional[bool]

    discovery_source: str
    retrieved_at: datetime

    signals: list = field(default_factory=list)


@dataclass
class EligibilityAuditItem:
    discovery_rank: int
    ticker: str
    company: str

    discovery_score: Optional[float]
    entry_reason: str

    eligibility_status: str
    eligible: bool
    eligibility_reason: str

    security_type: str
    market_cap: Optional[float]
    profitable: Optional[bool]
    net_income: Optional[float]

    eligibility_source: str
    eligibility_retrieved_at: datetime


@dataclass
class HistoryResult:
    ticker: str
    close: list
    volume: list

    retrieved_at: datetime
    source: str

    error: Optional[str] = None


# ============================================================
# ETF UNIVERSE
# ============================================================

MAJOR_ETFS = {
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
    "IWM": "iShares Russell 2000 ETF",
    "DIA": "SPDR Dow Jones Industrial Average ETF",
    "XLK": "Technology Select Sector SPDR Fund",
    "XLF": "Financial Select Sector SPDR Fund",
    "XLV": "Health Care Select Sector SPDR Fund",
    "XLY": "Consumer Discretionary Select Sector SPDR Fund",
    "XLP": "Consumer Staples Select Sector SPDR Fund",
    "XLI": "Industrial Select Sector SPDR Fund",
    "XLE": "Energy Select Sector SPDR Fund",
    "XLU": "Utilities Select Sector SPDR Fund",
    "XLRE": "Real Estate Select Sector SPDR Fund",
    "XLB": "Materials Select Sector SPDR Fund",
    "XLC": "Communication Services Select Sector SPDR Fund",
}


# ============================================================
# HTTP
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


# ============================================================
# HELPERS
# ============================================================

def safe_float(value):
    try:
        if value is None:
            return None

        value = float(value)

        if pd.isna(value):
            return None

        return value

    except Exception:
        return None


def pct_change(current, prior):
    if (
        current is None
        or prior is None
        or prior == 0
    ):
        return None

    return (
        current / prior
    ) - 1


def chunks(items, size):
    items = list(items)

    for i in range(
        0,
        len(items),
        size,
    ):
        yield items[i:i + size]


# ============================================================
# S&P 500 UNIVERSE
# ============================================================

def get_sp500_universe():
    url = (
        "https://en.wikipedia.org/wiki/"
        "List_of_S%26P_500_companies"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    tables = pd.read_html(
        io.StringIO(
            response.text
        )
    )

    if not tables:
        raise RuntimeError(
            "No S&P 500 table was returned."
        )

    table = tables[0]

    if (
        "Symbol" not in table.columns
        or "Security" not in table.columns
    ):
        raise RuntimeError(
            "S&P 500 table did not contain "
            "Symbol and Security columns."
        )

    universe = {}

    for _, row in table.iterrows():

        ticker = str(
            row["Symbol"]
        ).strip()

        company = str(
            row["Security"]
        ).strip()

        ticker = ticker.replace(
            ".",
            "-",
        )

        if ticker:
            universe[ticker] = company

    return universe


def build_discovery_universe():
    universe = get_sp500_universe()

    for ticker, company in MAJOR_ETFS.items():
        universe[ticker] = company

    return universe


# ============================================================
# YAHOO SPARK BATCH RETRIEVAL
# ============================================================

def fetch_spark_batch(
    tickers,
):
    """
    Retrieve daily close history for multiple symbols
    in one Yahoo request.

    This substantially reduces request count compared
    with one chart request per symbol.
    """

    ticker_list = [
        ticker.upper().strip()
        for ticker in tickers
    ]

    retrieved_at = datetime.now(
        timezone.utc
    )

    url = (
        "https://query1.finance.yahoo.com/"
        "v7/finance/spark"
    )

    params = {
        "symbols": ",".join(
            ticker_list
        ),
        "range": "1y",
        "interval": "1d",
        "indicators": "close,volume",
        "includeTimestamps": "true",
        "includePrePost": "false",
    }

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429:

                wait_seconds = (
                    2 ** attempt
                )

                time.sleep(
                    wait_seconds
                )

                last_error = (
                    "429 Too Many Requests"
                )

                continue

            response.raise_for_status()

            payload = response.json()

            return (
                payload,
                retrieved_at,
                None,
            )

        except Exception as exc:

            last_error = str(
                exc
            )

            if attempt < MAX_RETRIES:

                time.sleep(
                    1.5 * attempt
                )

    return (
        None,
        retrieved_at,
        last_error,
    )


# ============================================================
# PARSE SPARK
# ============================================================

def parse_spark_symbol(
    ticker,
    payload,
    retrieved_at,
):
    """
    Yahoo spark responses have changed shape over time.
    This parser handles the common keyed-symbol layouts.
    """

    if payload is None:

        return HistoryResult(
            ticker=ticker,
            close=[],
            volume=[],
            retrieved_at=retrieved_at,
            source="Yahoo Finance spark API",
            error="No spark payload returned.",
        )

    symbol_data = None

    # Common form:
    # {
    #   "AAPL": {...},
    #   "MSFT": {...}
    # }
    if ticker in payload:
        symbol_data = payload.get(
            ticker
        )

    # Alternate wrapper form.
    if symbol_data is None:

        spark = payload.get(
            "spark"
        )

        if isinstance(
            spark,
            dict,
        ):
            symbol_data = spark.get(
                ticker
            )

    if symbol_data is None:

        return HistoryResult(
            ticker=ticker,
            close=[],
            volume=[],
            retrieved_at=retrieved_at,
            source="Yahoo Finance spark API",
            error=(
                "Symbol was not present in "
                "Yahoo spark response."
            ),
        )

    # Some spark payloads put response data inside
    # a "response" array.
    if isinstance(
        symbol_data,
        dict,
    ):

        response_items = symbol_data.get(
            "response"
        )

        if (
            isinstance(
                response_items,
                list,
            )
            and response_items
        ):
            symbol_data = response_items[0]

    close_values = []
    volume_values = []

    if isinstance(
        symbol_data,
        dict,
    ):

        close_values = (
            symbol_data.get(
                "close"
            )
            or []
        )

        volume_values = (
            symbol_data.get(
                "volume"
            )
            or []
        )

        # Alternate chart-like spark structure.
        if not close_values:

            indicators = symbol_data.get(
                "indicators",
                {}
            )

            quotes = indicators.get(
                "quote",
                []
            )

            if quotes:

                close_values = (
                    quotes[0].get(
                        "close"
                    )
                    or []
                )

                volume_values = (
                    quotes[0].get(
                        "volume"
                    )
                    or []
                )

    close = [
        number
        for number in (
            safe_float(value)
            for value in close_values
        )
        if number is not None
    ]

    volume = [
        number
        for number in (
            safe_float(value)
            for value in volume_values
        )
        if number is not None
    ]

    if len(close) < 30:

        return HistoryResult(
            ticker=ticker,
            close=close,
            volume=volume,
            retrieved_at=retrieved_at,
            source="Yahoo Finance spark API",
            error=(
                "Fewer than 30 usable daily closes "
                "were returned."
            ),
        )

    return HistoryResult(
        ticker=ticker,
        close=close,
        volume=volume,
        retrieved_at=retrieved_at,
        source="Yahoo Finance spark API",
        error=None,
    )


# ============================================================
# COMPLETE HISTORY DOWNLOAD
# ============================================================

def download_history(
    tickers,
):
    """
    Retrieve the universe in moderate-size batches.

    About 500 symbols at batch size 25 means roughly
    20 requests instead of roughly 500.
    """

    ticker_list = list(
        tickers
    )

    results = {}

    for batch_number, batch in enumerate(
        chunks(
            ticker_list,
            BATCH_SIZE,
        ),
        start=1,
    ):

        (
            payload,
            retrieved_at,
            batch_error,
        ) = fetch_spark_batch(
            batch
        )

        if batch_error:

            for ticker in batch:

                results[ticker] = (
                    HistoryResult(
                        ticker=ticker,
                        close=[],
                        volume=[],
                        retrieved_at=retrieved_at,
                        source=(
                            "Yahoo Finance spark API"
                        ),
                        error=(
                            "Batch retrieval failed: "
                            f"{batch_error}"
                        ),
                    )
                )

        else:

            for ticker in batch:

                results[ticker] = (
                    parse_spark_symbol(
                        ticker,
                        payload,
                        retrieved_at,
                    )
                )

        time.sleep(
            BATCH_PAUSE_SECONDS
        )

    return results


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    history_result,
):
    if history_result is None:
        return None

    if history_result.error:
        return None

    close = history_result.close
    volume = history_result.volume

    if len(close) < 30:
        return None

    current_price = safe_float(
        close[-1]
    )

    if current_price is None:
        return None

    return_1d = None
    return_1m = None
    return_3m = None
    return_6m = None

    if len(close) >= 2:
        return_1d = pct_change(
            current_price,
            safe_float(
                close[-2]
            ),
        )

    if len(close) >= 22:
        return_1m = pct_change(
            current_price,
            safe_float(
                close[-22]
            ),
        )

    if len(close) >= 64:
        return_3m = pct_change(
            current_price,
            safe_float(
                close[-64]
            ),
        )

    if len(close) >= 127:
        return_6m = pct_change(
            current_price,
            safe_float(
                close[-127]
            ),
        )

    high_52w = max(
        close
    )

    low_52w = min(
        close
    )

    drawdown_from_high = None

    if high_52w > 0:
        drawdown_from_high = (
            current_price / high_52w
        ) - 1

    distance_from_low = None

    if low_52w > 0:
        distance_from_low = (
            current_price / low_52w
        ) - 1

    volume_ratio = None

    if len(volume) >= 21:

        current_volume = safe_float(
            volume[-1]
        )

        prior_volumes = [
            safe_float(value)
            for value in volume[-21:-1]
        ]

        prior_volumes = [
            value
            for value in prior_volumes
            if value is not None
        ]

        if prior_volumes:

            average_volume = (
                sum(prior_volumes)
                / len(prior_volumes)
            )

            if (
                current_volume is not None
                and average_volume > 0
            ):
                volume_ratio = (
                    current_volume
                    / average_volume
                )

    return {
        "last_price":
            current_price,

        "return_1d":
            return_1d,

        "return_1m":
            return_1m,

        "return_3m":
            return_3m,

        "return_6m":
            return_6m,

        "drawdown_from_52w_high":
            drawdown_from_high,

        "distance_from_52w_low":
            distance_from_low,

        "volume_ratio":
            volume_ratio,
    }


# ============================================================
# SIGNALS
# ============================================================

def build_signals(
    metrics,
):
    signals = []

    r1d = metrics.get(
        "return_1d"
    )

    r1m = metrics.get(
        "return_1m"
    )

    r3m = metrics.get(
        "return_3m"
    )

    r6m = metrics.get(
        "return_6m"
    )

    drawdown = metrics.get(
        "drawdown_from_52w_high"
    )

    low_distance = metrics.get(
        "distance_from_52w_low"
    )

    volume_ratio = metrics.get(
        "volume_ratio"
    )

    if (
        r1d is not None
        and r1d <= -0.05
    ):
        signals.append(
            f"1-day decline {r1d:.1%}"
        )

    if (
        r1m is not None
        and r1m <= -0.10
    ):
        signals.append(
            f"1-month decline {r1m:.1%}"
        )

    if (
        r3m is not None
        and r3m <= -0.15
    ):
        signals.append(
            f"3-month decline {r3m:.1%}"
        )

    if (
        r6m is not None
        and r6m <= -0.20
    ):
        signals.append(
            f"6-month decline {r6m:.1%}"
        )

    if (
        drawdown is not None
        and drawdown <= -0.25
    ):
        signals.append(
            f"{abs(drawdown):.1%} below 52-week high"
        )

    if (
        low_distance is not None
        and low_distance <= 0.10
    ):
        signals.append(
            f"within {low_distance:.1%} of 52-week low"
        )

    if (
        volume_ratio is not None
        and volume_ratio >= 1.75
    ):
        signals.append(
            f"volume {volume_ratio:.1f}× recent average"
        )

    return signals


# ============================================================
# SCORE
# ============================================================

def calculate_discovery_score(
    metrics,
):
    score = 0.0

    r1d = metrics.get(
        "return_1d"
    )

    r1m = metrics.get(
        "return_1m"
    )

    r3m = metrics.get(
        "return_3m"
    )

    r6m = metrics.get(
        "return_6m"
    )

    drawdown = metrics.get(
        "drawdown_from_52w_high"
    )

    low_distance = metrics.get(
        "distance_from_52w_low"
    )

    volume_ratio = metrics.get(
        "volume_ratio"
    )

    if r1d is not None:
        score += (
            max(
                0,
                -r1d,
            )
            * 150
        )

    if r1m is not None:
        score += (
            max(
                0,
                -r1m,
            )
            * 125
        )

    if r3m is not None:
        score += (
            max(
                0,
                -r3m,
            )
            * 100
        )

    if r6m is not None:
        score += (
            max(
                0,
                -r6m,
            )
            * 75
        )

    if drawdown is not None:
        score += (
            max(
                0,
                -drawdown,
            )
            * 75
        )

    if (
        low_distance is not None
        and low_distance >= 0
    ):
        score += (
            max(
                0,
                0.20 - low_distance,
            )
            * 50
        )

    if (
        volume_ratio is not None
        and volume_ratio > 1
    ):
        score += (
            min(
                volume_ratio - 1,
                3,
            )
            * 2
        )

    return float(
        score
    )


# ============================================================
# ENTRY REASON
# ============================================================

def build_entry_reason(
    signals,
):
    if not signals:

        return (
            "Entered because current market data showed "
            "an elevated dislocation score."
        )

    return (
        "Entered the screen because of current market "
        "dislocation: "
        + "; ".join(
            signals[:3]
        )
        + "."
    )


# ============================================================
# RANKED DISCOVERY POOL
# ============================================================

def build_ranked_dislocation_pool():
    universe = build_discovery_universe()

    history_results = download_history(
        universe.keys()
    )

    failures = [
        ticker
        for ticker, result
        in history_results.items()
        if result.error
    ]

    total = len(
        history_results
    )

    failure_rate = (
        len(failures) / total
        if total > 0
        else 1.0
    )

    if failure_rate > MAX_FAILURE_RATE:

        sample = ", ".join(
            failures[:20]
        )

        raise RuntimeError(
            "Discovery data retrieval was materially "
            "incomplete. "
            f"{len(failures)} of {total} symbols failed "
            f"({failure_rate:.1%}). "
            f"Examples: {sample}"
        )

    pool = []

    for ticker, company in universe.items():

        history_result = (
            history_results.get(
                ticker
            )
        )

        if (
            history_result is None
            or history_result.error
        ):
            continue

        metrics = calculate_metrics(
            history_result
        )

        if metrics is None:
            continue

        signals = build_signals(
            metrics
        )

        if not signals:
            continue

        score = calculate_discovery_score(
            metrics
        )

        pool.append(
            {
                "ticker":
                    ticker,

                "company":
                    company,

                "metrics":
                    metrics,

                "signals":
                    signals,

                "score":
                    score,

                "retrieved_at":
                    history_result.retrieved_at,

                "history_source":
                    history_result.source,
            }
        )

    pool.sort(
        key=lambda item: (
            -item["score"],
            item["ticker"],
        )
    )

    return pool


# ============================================================
# DISCOVER + ELIGIBILITY + FREEZE
# ============================================================

def discover_candidates(
    target_count=12,
):
    ranked_pool = (
        build_ranked_dislocation_pool()
    )

    frozen_candidates = []
    eligibility_audit = []

    for discovery_rank, item in enumerate(
        ranked_pool,
        start=1,
    ):

        ticker = item[
            "ticker"
        ]

        eligibility = evaluate_eligibility(
            ticker
        )

        entry_reason = build_entry_reason(
            item["signals"]
        )

        eligibility_audit.append(
            EligibilityAuditItem(
                discovery_rank=discovery_rank,

                ticker=ticker,

                company=item[
                    "company"
                ],

                discovery_score=item[
                    "score"
                ],

                entry_reason=entry_reason,

                eligibility_status=(
                    eligibility.status
                ),

                eligible=(
                    eligibility.eligible
                ),

                eligibility_reason=(
                    eligibility.reason
                ),

                security_type=(
                    eligibility.security_type
                ),

                market_cap=(
                    eligibility.market_cap
                ),

                profitable=(
                    eligibility.profitable
                ),

                net_income=(
                    eligibility.net_income
                ),

                eligibility_source=(
                    eligibility.source
                ),

                eligibility_retrieved_at=(
                    eligibility.retrieved_at
                ),
            )
        )

        if not eligibility.eligible:
            continue

        if (
            len(frozen_candidates)
            >= target_count
        ):
            continue

        metrics = item[
            "metrics"
        ]

        frozen_candidates.append(
            DiscoveredCandidate(
                ticker=ticker,

                company=item[
                    "company"
                ],

                entry_reason=entry_reason,

                last_price=metrics[
                    "last_price"
                ],

                return_1d=metrics[
                    "return_1d"
                ],

                return_1m=metrics[
                    "return_1m"
                ],

                return_3m=metrics[
                    "return_3m"
                ],

                return_6m=metrics[
                    "return_6m"
                ],

                drawdown_from_52w_high=(
                    metrics[
                        "drawdown_from_52w_high"
                    ]
                ),

                distance_from_52w_low=(
                    metrics[
                        "distance_from_52w_low"
                    ]
                ),

                volume_ratio=metrics[
                    "volume_ratio"
                ],

                discovery_score=item[
                    "score"
                ],

                eligibility_status=(
                    eligibility.status
                ),

                eligibility_reason=(
                    eligibility.reason
                ),

                market_cap=(
                    eligibility.market_cap
                ),

                profitable=(
                    eligibility.profitable
                ),

                discovery_source=(
                    f"{item['history_source']}; "
                    "batched historical retrieval; "
                    "eligibility checked before freeze"
                ),

                retrieved_at=item[
                    "retrieved_at"
                ],

                signals=item[
                    "signals"
                ],
            )
        )

    return (
        frozen_candidates,
        eligibility_audit,
    )
