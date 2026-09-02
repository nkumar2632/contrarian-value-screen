from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import io

import pandas as pd
import requests
import yfinance as yf

from eligibility import evaluate_eligibility


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
# S&P 500 UNIVERSE
# ============================================================

def get_sp500_universe():
    url = (
        "https://en.wikipedia.org/wiki/"
        "List_of_S%26P_500_companies"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
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
            "No tables found on the S&P 500 source page."
        )

    table = tables[0]

    if (
        "Symbol" not in table.columns
        or "Security" not in table.columns
    ):
        raise RuntimeError(
            "Expected S&P 500 columns were not found."
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

    if not universe:
        raise RuntimeError(
            "The S&P 500 universe was empty."
        )

    return universe


# ============================================================
# BUILD DISCOVERY UNIVERSE
# ============================================================

def build_discovery_universe():

    universe = get_sp500_universe()

    for ticker, company in MAJOR_ETFS.items():
        universe[ticker] = company

    return universe


# ============================================================
# MARKET HISTORY
# ============================================================

def download_history(tickers):

    ticker_list = list(
        tickers
    )

    if not ticker_list:
        raise RuntimeError(
            "No tickers supplied for discovery."
        )

    data = yf.download(
        tickers=ticker_list,
        period="1y",
        interval="1d",
        group_by="column",
        auto_adjust=False,
        progress=False,
        threads=True,
    )

    if (
        data is None
        or data.empty
    ):
        raise RuntimeError(
            "No market history returned."
        )

    return data


# ============================================================
# SAFE HELPERS
# ============================================================

def safe_float(value):

    try:

        if pd.isna(value):
            return None

        return float(value)

    except Exception:
        return None


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
# EXTRACT TICKER SERIES
# ============================================================

def get_ticker_series(
    data,
    field,
    ticker,
):

    try:

        field_data = data[
            field
        ]

        if isinstance(
            field_data,
            pd.Series,
        ):
            return field_data.dropna()

        if ticker not in field_data.columns:
            return pd.Series(
                dtype=float
            )

        return field_data[
            ticker
        ].dropna()

    except Exception:

        return pd.Series(
            dtype=float
        )


# ============================================================
# METRIC CALCULATION
# ============================================================

def calculate_metrics(
    ticker,
    data,
):

    close = get_ticker_series(
        data,
        "Close",
        ticker,
    )

    volume = get_ticker_series(
        data,
        "Volume",
        ticker,
    )

    if len(close) < 30:
        return None

    current_price = safe_float(
        close.iloc[-1]
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
                close.iloc[-2]
            ),
        )

    if len(close) >= 22:

        return_1m = pct_change(
            current_price,
            safe_float(
                close.iloc[-22]
            ),
        )

    if len(close) >= 64:

        return_3m = pct_change(
            current_price,
            safe_float(
                close.iloc[-64]
            ),
        )

    if len(close) >= 127:

        return_6m = pct_change(
            current_price,
            safe_float(
                close.iloc[-127]
            ),
        )

    high_52w = safe_float(
        close.max()
    )

    low_52w = safe_float(
        close.min()
    )

    drawdown_from_high = None

    if (
        high_52w is not None
        and high_52w > 0
    ):

        drawdown_from_high = (
            current_price / high_52w
        ) - 1

    distance_from_low = None

    if (
        low_52w is not None
        and low_52w > 0
    ):

        distance_from_low = (
            current_price / low_52w
        ) - 1

    volume_ratio = None

    if len(volume) >= 21:

        current_volume = safe_float(
            volume.iloc[-1]
        )

        average_volume = safe_float(
            volume.iloc[-21:-1].mean()
        )

        if (
            current_volume is not None
            and average_volume is not None
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
    Create the complete ranked pool of securities that
    triggered at least one discovery signal.
    """

    retrieved_at = datetime.now(
        timezone.utc
    )

    universe = build_discovery_universe()

    tickers = list(
        universe.keys()
    )

    history = download_history(
        tickers
    )

    pool = []

    for ticker in tickers:

        metrics = calculate_metrics(
            ticker,
            history,
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
                    universe[ticker],

                "metrics":
                    metrics,

                "signals":
                    signals,

                "score":
                    score,

                "retrieved_at":
                    retrieved_at,
            }
        )

    pool.sort(
        key=lambda item: item["score"],
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

    1. Build the complete ranked dislocation pool.
    2. Evaluate eligibility for every security in the pool.
    3. Record every eligibility decision.
    4. Freeze only the first target_count eligible securities.
    5. Continue auditing after the frozen list is full.

    Returns:
        frozen_candidates
        eligibility_audit
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
                    "Yahoo Finance daily market data; "
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
