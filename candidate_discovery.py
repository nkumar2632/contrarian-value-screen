from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import time

import pandas as pd
import requests

from eligibility import evaluate_eligibility


# ============================================================
# SETTINGS
# ============================================================

YAHOO_TIMEOUT_SECONDS = 15
YAHOO_RETRIES = 3
MAX_WORKERS = 8


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
# MAJOR UNLEVERAGED ETF UNIVERSE
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
# HTTP HEADERS
# ============================================================

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
}


# ============================================================
# S&P 500 UNIVERSE
# ============================================================

def get_sp500_universe():
    """
    Retrieve the current S&P 500 constituent list.

    requests performs the HTTP retrieval.
    pandas parses only the already-downloaded HTML.
    """

    url = (
        "https://en.wikipedia.org/wiki/"
        "List_of_S%26P_500_companies"
    )

    response = requests.get(
        url,
        headers=HTTP_HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    tables = pd.read_html(
        io.StringIO(
            response.text
        )
    )

    if not tables:
        raise RuntimeError(
            "No S&P 500 tables were returned."
        )

    table = tables[0]

    if (
        "Symbol" not in table.columns
        or "Security" not in table.columns
    ):
        raise RuntimeError(
            "Expected Symbol and Security columns "
            "were not found in the S&P 500 table."
        )

    universe = {}

    for _, row in table.iterrows():

        ticker = str(
            row["Symbol"]
        ).strip()

        company = str(
            row["Security"]
        ).strip()

        # Yahoo format for BRK.B etc.
        ticker = ticker.replace(
            ".",
            "-",
        )

        if ticker:
            universe[ticker] = company

    if not universe:
        raise RuntimeError(
            "S&P 500 universe was empty after parsing."
        )

    return universe


# ============================================================
# COMPLETE DISCOVERY UNIVERSE
# ============================================================

def build_discovery_universe():

    universe = get_sp500_universe()

    for ticker, company in MAJOR_ETFS.items():
        universe[ticker] = company

    return universe


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_float(value):

    try:

        if value is None:
            return None

        value = float(
            value
        )

        if pd.isna(
            value
        ):
            return None

        return value

    except Exception:
        return None


# ============================================================
# DIRECT YAHOO HISTORY RETRIEVAL
# ============================================================

def get_yahoo_history(
    ticker,
):
    """
    Retrieve approximately one year of daily history directly
    from Yahoo's chart endpoint.

    No yfinance bulk download is used.

    Each ticker is independently retrieved so one malformed
    ticker cannot corrupt the entire universe download.
    """

    ticker = ticker.upper().strip()

    url = (
        "https://query1.finance.yahoo.com/"
        "v8/finance/chart/"
        f"{ticker}"
        "?range=1y"
        "&interval=1d"
        "&includePrePost=false"
        "&events=div%2Csplits"
    )

    last_error = None

    for attempt in range(
        1,
        YAHOO_RETRIES + 1,
    ):

        retrieved_at = datetime.now(
            timezone.utc
        )

        try:

            response = requests.get(
                url,
                headers=HTTP_HEADERS,
                timeout=YAHOO_TIMEOUT_SECONDS,
            )

            response.raise_for_status()

            payload = response.json()

            chart = payload.get(
                "chart",
                {}
            )

            chart_error = chart.get(
                "error"
            )

            if chart_error:
                raise RuntimeError(
                    str(chart_error)
                )

            results = chart.get(
                "result"
            )

            if not results:
                raise RuntimeError(
                    "Yahoo returned no chart result."
                )

            result = results[0]

            indicators = result.get(
                "indicators",
                {}
            )

            quotes = indicators.get(
                "quote"
            )

            if not quotes:
                raise RuntimeError(
                    "Yahoo returned no quote history."
                )

            quote = quotes[0]

            close_values = quote.get(
                "close",
                []
            )

            volume_values = quote.get(
                "volume",
                []
            )

            if not close_values:
                raise RuntimeError(
                    "Yahoo returned no closing-price history."
                )

            close = []

            volume = []

            for value in close_values:

                number = safe_float(
                    value
                )

                if number is not None:
                    close.append(
                        number
                    )

            for value in volume_values:

                number = safe_float(
                    value
                )

                if number is not None:
                    volume.append(
                        number
                    )

            if len(close) < 30:
                raise RuntimeError(
                    "Fewer than 30 usable daily closes "
                    "were returned."
                )

            return HistoryResult(
                ticker=ticker,
                close=close,
                volume=volume,
                retrieved_at=retrieved_at,
                source="Yahoo Finance chart API",
                error=None,
            )

        except Exception as exc:

            last_error = str(
                exc
            )

            if attempt < YAHOO_RETRIES:

                time.sleep(
                    0.4 * attempt
                )

    return HistoryResult(
        ticker=ticker,
        close=[],
        volume=[],
        retrieved_at=datetime.now(
            timezone.utc
        ),
        source="Yahoo Finance chart API",
        error=last_error,
    )


# ============================================================
# RETRIEVE COMPLETE UNIVERSE HISTORY
# ============================================================

def download_history(
    tickers,
):
    """
    Retrieve each ticker independently.

    Uses moderate parallelism to avoid the unreliable
    yfinance multi-ticker bulk download while keeping
    runtime reasonable.
    """

    ticker_list = list(
        tickers
    )

    if not ticker_list:
        raise RuntimeError(
            "No tickers supplied for discovery."
        )

    results = {}

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_map = {
            executor.submit(
                get_yahoo_history,
                ticker,
            ): ticker
            for ticker in ticker_list
        }

        for future in as_completed(
            future_map
        ):

            ticker = future_map[
                future
            ]

            try:

                result = future.result()

            except Exception as exc:

                result = HistoryResult(
                    ticker=ticker,
                    close=[],
                    volume=[],
                    retrieved_at=datetime.now(
                        timezone.utc
                    ),
                    source="Yahoo Finance chart API",
                    error=str(exc),
                )

            results[
                ticker
            ] = result

    return results


# ============================================================
# PERCENT CHANGE
# ============================================================

def pct_change(
    current,
    prior,
):

    if (
        current is None
        or prior is None
        or prior == 0
    ):
        return None

    return (
        current / prior
    ) - 1


# ============================================================
# METRIC CALCULATION
# ============================================================

def calculate_metrics(
    history_result,
):
    """
    Calculate discovery metrics from one independently
    retrieved ticker history.
    """

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

        recent_volume = volume[
            -21:
        ]

        current_volume = safe_float(
            recent_volume[-1]
        )

        prior_volumes = recent_volume[
            :-1
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
# DISCOVERY SIGNALS
# ============================================================

def build_signals(
    metrics,
):
    """
    These are candidate-discovery signals only.

    They do not establish valuation and cannot pass Gate 1.
    """

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
# DISCOVERY SCORE
# ============================================================

def calculate_discovery_score(
    metrics,
):
    """
    Rank observable dislocations.

    This score is not an investment score and cannot
    pass any valuation gate.
    """

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
    """
    Retrieve the entire universe independently and build
    the complete ranked pool of qualifying dislocations.
    """

    universe = build_discovery_universe()

    history_results = download_history(
        universe.keys()
    )

    # --------------------------------------------------------
    # DATA-INTEGRITY CHECK
    # --------------------------------------------------------

    retrieval_failures = [
        ticker
        for ticker, result
        in history_results.items()
        if result.error
    ]

    success_count = (
        len(history_results)
        - len(retrieval_failures)
    )

    if success_count == 0:

        raise RuntimeError(
            "Yahoo history retrieval failed for the "
            "entire discovery universe."
        )

    failure_rate = (
        len(retrieval_failures)
        / len(history_results)
    )

    # Do not silently pretend a badly incomplete universe
    # was successfully screened.
    if failure_rate > 0.10:

        sample = ", ".join(
            retrieval_failures[:15]
        )

        raise RuntimeError(
            "Discovery data retrieval was materially "
            "incomplete. "
            f"{len(retrieval_failures)} of "
            f"{len(history_results)} symbols failed. "
            f"Examples: {sample}"
        )

    pool = []

    for ticker, company in universe.items():

        history_result = history_results.get(
            ticker
        )

        if history_result is None:
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
            item["score"],
            item["ticker"],
        ),
        reverse=True,
    )

    return pool


# ============================================================
# ELIGIBILITY AUDIT + FREEZE
# ============================================================

def discover_candidates(
    target_count=12,
):
    """
    v6.3.1 discovery sequence:

    1. Retrieve current S&P 500 + major ETF history.
    2. Calculate current market-dislocation signals.
    3. Rank the complete qualifying dislocation pool.
    4. Evaluate eligibility for every ranked candidate.
    5. Record every eligibility result.
    6. Freeze only the first target_count eligible names.
    7. Continue the audit after the frozen list is full.

    Investment gating begins only after this function
    returns the frozen list.
    """

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
                    "S&P 500 constituent list retrieved "
                    "with requests and parsed locally; "
                    "eligibility evaluated before final "
                    "candidate freeze"
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
