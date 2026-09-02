from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf


# ============================================================
# CONSTANTS
# ============================================================

MINIMUM_MARKET_CAP = 10_000_000_000


# ============================================================
# RESULT
# ============================================================

@dataclass
class EligibilityResult:
    ticker: str

    eligible: bool
    status: str
    reason: str

    security_type: str

    market_cap: Optional[float]
    profitable: Optional[bool]
    net_income: Optional[float]

    source: str
    retrieved_at: datetime


# ============================================================
# ETF IDENTIFICATION
# ============================================================

KNOWN_ETFS = {
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "XLK",
    "XLF",
    "XLV",
    "XLY",
    "XLP",
    "XLI",
    "XLE",
    "XLU",
    "XLRE",
    "XLB",
    "XLC",
}


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_float(value):
    try:
        if value is None:
            return None

        return float(value)

    except Exception:
        return None


# ============================================================
# NET INCOME RETRIEVAL
# ============================================================

def get_latest_annual_net_income(stock):
    """
    Retrieve the most recent available annual net income.

    Returns None if a usable value cannot be obtained.
    """

    try:
        income_stmt = stock.get_income_stmt(
            freq="yearly"
        )

        if (
            income_stmt is None
            or income_stmt.empty
        ):
            return None

        possible_rows = [
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income Including Noncontrolling Interests",
        ]

        for row_name in possible_rows:

            if row_name not in income_stmt.index:
                continue

            values = income_stmt.loc[
                row_name
            ].dropna()

            if values.empty:
                continue

            value = safe_float(
                values.iloc[0]
            )

            if value is not None:
                return value

    except Exception:
        return None

    return None


# ============================================================
# FALLBACK PROFITABILITY
# ============================================================

def get_profitability_from_info(info):
    """
    Fallback profitability evidence.

    trailingEps > 0 or profitMargins > 0 can establish
    positive trailing profitability when annual statement
    retrieval is unavailable.

    This is a fallback, not the preferred source.
    """

    trailing_eps = safe_float(
        info.get("trailingEps")
    )

    profit_margin = safe_float(
        info.get("profitMargins")
    )

    if trailing_eps is not None:
        return trailing_eps > 0

    if profit_margin is not None:
        return profit_margin > 0

    return None


# ============================================================
# ETF ELIGIBILITY
# ============================================================

def evaluate_etf_eligibility(
    ticker,
):
    """
    Major unleveraged ETFs in our predefined discovery
    universe are eligible for discovery without applying
    corporate market-cap or profitability tests.
    """

    return EligibilityResult(
        ticker=ticker,
        eligible=True,
        status="ELIGIBLE",
        reason=(
            "Major unleveraged ETF in the predefined "
            "v6.3.1 discovery universe."
        ),
        security_type="ETF",
        market_cap=None,
        profitable=None,
        net_income=None,
        source=(
            "Predefined major unleveraged ETF universe"
        ),
        retrieved_at=datetime.now(
            timezone.utc
        ),
    )


# ============================================================
# STOCK ELIGIBILITY
# ============================================================

def evaluate_stock_eligibility(
    ticker,
):
    """
    v6.3.1 stock eligibility:

    1. Approximately $10B or greater market capitalization.
    2. Profitable.

    Missing essential eligibility data produces
    DATA INSUFFICIENT rather than an investment-gate failure.
    """

    retrieved_at = datetime.now(
        timezone.utc
    )

    try:
        stock = yf.Ticker(
            ticker
        )

        info = stock.get_info()

    except Exception as exc:

        return EligibilityResult(
            ticker=ticker,
            eligible=False,
            status="DATA INSUFFICIENT",
            reason=(
                "Could not retrieve company information "
                f"required for eligibility: {exc}"
            ),
            security_type="STOCK",
            market_cap=None,
            profitable=None,
            net_income=None,
            source="Yahoo Finance",
            retrieved_at=retrieved_at,
        )

    if not isinstance(
        info,
        dict,
    ):

        info = {}

    # --------------------------------------------------------
    # MARKET CAP
    # --------------------------------------------------------

    market_cap = safe_float(
        info.get("marketCap")
    )

    # --------------------------------------------------------
    # PROFITABILITY
    # --------------------------------------------------------

    net_income = (
        get_latest_annual_net_income(
            stock
        )
    )

    profitable = None

    if net_income is not None:

        profitable = (
            net_income > 0
        )

    else:

        profitable = (
            get_profitability_from_info(
                info
            )
        )

    # --------------------------------------------------------
    # MISSING DATA
    # --------------------------------------------------------

    missing = []

    if market_cap is None:
        missing.append(
            "market capitalization"
        )

    if profitable is None:
        missing.append(
            "profitability"
        )

    if missing:

        return EligibilityResult(
            ticker=ticker,
            eligible=False,
            status="DATA INSUFFICIENT",
            reason=(
                "Eligibility could not be established because "
                + " and ".join(missing)
                + " could not be retrieved reliably."
            ),
            security_type="STOCK",
            market_cap=market_cap,
            profitable=profitable,
            net_income=net_income,
            source="Yahoo Finance",
            retrieved_at=retrieved_at,
        )

    # --------------------------------------------------------
    # MARKET CAP EXCLUSION
    # --------------------------------------------------------

    if market_cap < MINIMUM_MARKET_CAP:

        return EligibilityResult(
            ticker=ticker,
            eligible=False,
            status="INELIGIBLE",
            reason=(
                f"Market capitalization ${market_cap / 1e9:.1f}B "
                "is below the approximately $10B "
                "v6.3.1 discovery threshold."
            ),
            security_type="STOCK",
            market_cap=market_cap,
            profitable=profitable,
            net_income=net_income,
            source="Yahoo Finance",
            retrieved_at=retrieved_at,
        )

    # --------------------------------------------------------
    # PROFITABILITY EXCLUSION
    # --------------------------------------------------------

    if not profitable:

        return EligibilityResult(
            ticker=ticker,
            eligible=False,
            status="INELIGIBLE",
            reason=(
                "The company does not meet the profitable-company "
                "requirement for the v6.3.1 discovery universe."
            ),
            security_type="STOCK",
            market_cap=market_cap,
            profitable=profitable,
            net_income=net_income,
            source="Yahoo Finance",
            retrieved_at=retrieved_at,
        )

    # --------------------------------------------------------
    # PASS
    # --------------------------------------------------------

    return EligibilityResult(
        ticker=ticker,
        eligible=True,
        status="ELIGIBLE",
        reason=(
            f"Market capitalization ${market_cap / 1e9:.1f}B "
            "and positive profitability satisfy the "
            "v6.3.1 discovery eligibility requirements."
        ),
        security_type="STOCK",
        market_cap=market_cap,
        profitable=True,
        net_income=net_income,
        source="Yahoo Finance",
        retrieved_at=retrieved_at,
    )


# ============================================================
# MAIN ELIGIBILITY FUNCTION
# ============================================================

def evaluate_eligibility(
    ticker,
):
    """
    Route ETFs and operating companies through the
    appropriate eligibility logic.
    """

    ticker = ticker.upper().strip()

    if ticker in KNOWN_ETFS:

        return evaluate_etf_eligibility(
            ticker
        )

    return evaluate_stock_eligibility(
        ticker
    )
