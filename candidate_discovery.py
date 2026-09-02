from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf


# ============================================================
# DISCOVERY RESULT
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

    discovery_source: str
    retrieved_at: datetime

    signals: list = field(
        default_factory=list
    )


# ============================================================
# MAJOR ETF UNIVERSE
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
# LARGE-CAP STOCK UNIVERSE
# ============================================================

def get_sp500_universe():
    """
    Retrieve the current S&P 500 constituent list.

    This is a reproducible large-cap discovery universe.

    It is NOT represented as the entire U.S. market.
    """

    url = (
        "https://en.wikipedia.org/wiki/"
        "List_of_S%26P_500_companies"
    )

    tables = pd.read_html(url)

    table = tables[0]

    universe = {}

    for _, row in table.iterrows():

        ticker = str(
            row["Symbol"]
        ).strip()

        company = str(
            row["Security"]
        ).strip()

        # Yahoo Finance uses '-' instead of '.'
        ticker = ticker.replace(
            ".",
            "-",
        )

        universe[ticker] = company

    return universe


# ============================================================
# FULL DISCOVERY UNIVERSE
# ============================================================

def build_discovery_universe():

    universe = get_sp500_universe()

    for ticker, name in MAJOR_ETFS.items():
        universe[ticker] = name

    return universe


# ============================================================
# DOWNLOAD PRICE HISTORY
# ============================================================

def download_history(
    tickers,
):
    """
    Download approximately one year of daily price and
    volume history.

    auto_adjust=False keeps directly reported historical
    OHLC data available.
    """

    data = yf.download(
        tickers=list(tickers),
        period="1y",
        interval="1d",
        group_by="column",
        auto_adjust=False,
        progress=False,
        threads=True,
    )

    return data


# ============================================================
# SAFE VALUE HELPERS
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
# PER-TICKER METRICS
# ============================================================

def calculate_metrics(
    ticker,
    data,
):

    try:

        close = data["Close"][ticker].dropna()

        volume = data["Volume"][ticker].dropna()

    except Exception:

        return None

    if len(close) < 30:
        return None

    current_price = safe_float(
        close.iloc[-1]
    )

    if current_price is None:
        return None

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    return_1d = None
    return_1m = None
    return_3m = None
    return_6m = None

    if len(close) >= 2:

        return_1d = pct_change(
            current_price,
            safe_float(close.iloc[-2]),
        )

    if len(close) >= 22:

        return_1m = pct_change(
            current_price,
            safe_float(close.iloc[-22]),
        )

    if len(close) >= 64:

        return_3m = pct_change(
            current_price,
            safe_float(close.iloc[-64]),
        )

    if len(close) >= 127:

        return_6m = pct_change(
            current_price,
            safe_float(close.iloc[-127]),
        )

    # --------------------------------------------------------
    # 52-WEEK RANGE
    # --------------------------------------------------------

    high_52w = safe_float(
        close.max()
    )

    low_52w = safe_float(
        close.min()
    )

    drawdown_from_high = None
    distance_from_low = None

    if (
        high_52w is not None
        and high_52w > 0
    ):

        drawdown_from_high = (
            current_price / high_52w
        ) - 1

    if (
        low_52w is not None
        and low_52w > 0
    ):

        distance_from_low = (
            current_price / low_52w
        ) - 1

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # PRICE DISLOCATION SIGNALS
    # --------------------------------------------------------

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
    Score current market dislocation.

    Higher score = larger observable dislocation.

    This score is ONLY for candidate discovery.

    It is NOT evidence that a security is undervalued,
    mispriced, or investable.
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
            * 100
            * 1.5
        )

    if r1m is not None:

        score += (
            max(
                0,
                -r1m,
            )
            * 100
            * 1.25
        )

    if r3m is not None:

        score += (
            max(
                0,
                -r3m,
            )
            * 100
            * 1.0
        )

    if r6m is not None:

        score += (
            max(
                0,
                -r6m,
            )
            * 100
            * 0.75
        )

    if drawdown is not None:

        score += (
            max(
                0,
                -drawdown,
            )
            * 100
            * 0.75
        )

    if (
        low_distance is not None
        and low_distance >= 0
    ):

        # Extra weight when price is close to
        # its 52-week low.

        score += (
            max(
                0,
                0.20 - low_distance,
            )
            * 100
            * 0.5
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

    return score


# ============================================================
# ENTRY REASON
# ============================================================

def build_entry_reason(
    signals,
):

    if not signals:

        return (
            "Current price behavior showed an elevated "
            "dislocation score relative to the discovery universe."
        )

    strongest = signals[:3]

    return (
        "Entered the screen because of current market "
        "dislocation: "
        + "; ".join(strongest)
        + "."
    )


# ============================================================
# DISCOVER AND FREEZE CANDIDATES
# ============================================================

def discover_candidates(
    target_count=12,
):
    """
    Discover candidates BEFORE any investment gates run.

    The returned list is the frozen candidate list.

    No replacement securities should be added later
    because other candidates fail gates.
    """

    retrieved_at = datetime.now(
        timezone.utc
    )

    universe = (
        build_discovery_universe()
    )

    tickers = list(
        universe.keys()
    )

    history = download_history(
        tickers
    )

    candidates = []

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

        score = calculate_discovery_score(
            metrics
        )

        # Require at least one meaningful
        # observable dislocation signal.

        if not signals:
            continue

        candidate = DiscoveredCandidate(
            ticker=ticker,

            company=universe[
                ticker
            ],

            entry_reason=(
                build_entry_reason(
                    signals
                )
            ),

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

            discovery_score=score,

            discovery_source=(
                "Yahoo Finance daily market data; "
                "S&P 500 constituent universe from Wikipedia"
            ),

            retrieved_at=retrieved_at,

            signals=signals,
        )

        candidates.append(
            candidate
        )

    # --------------------------------------------------------
    # RANK BEFORE GATING
    # --------------------------------------------------------

    candidates.sort(
        key=lambda x: (
            x.discovery_score
            if x.discovery_score
            is not None
            else -999
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # FREEZE LIST
    # --------------------------------------------------------

    frozen = candidates[
        :target_count
    ]

    return frozen
