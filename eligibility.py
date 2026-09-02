from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import time

import requests


# ============================================================
# SETTINGS
# ============================================================

MINIMUM_MARKET_CAP = 10_000_000_000

REQUEST_TIMEOUT = 12
MAX_RETRIES = 3


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
# ETF UNIVERSE
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
# SAFE HELPERS
# ============================================================

def safe_float(value):
    try:
        if value is None:
            return None

        return float(value)

    except Exception:
        return None


def raw_value(value):
    """
    Yahoo quoteSummary usually represents numerical fields as:

        {"raw": 123, "fmt": "123"}

    This safely extracts the raw number.
    """

    if value is None:
        return None

    if isinstance(value, dict):
        return safe_float(
            value.get("raw")
        )

    return safe_float(
        value
    )


# ============================================================
# YAHOO AUTH SESSION
# ============================================================

def create_yahoo_session():
    """
    Create a Yahoo session and retrieve the crumb token needed
    for quoteSummary requests.
    """

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    # Yahoo commonly sets the A3 cookie here.
    try:
        session.get(
            "https://fc.yahoo.com",
            timeout=REQUEST_TIMEOUT,
        )
    except Exception:
        pass

    crumb_response = session.get(
        "https://query1.finance.yahoo.com/v1/test/getcrumb",
        timeout=REQUEST_TIMEOUT,
    )

    crumb_response.raise_for_status()

    crumb = crumb_response.text.strip()

    if not crumb:
        raise RuntimeError(
            "Yahoo crumb token was empty."
        )

    return (
        session,
        crumb,
    )


# ============================================================
# QUOTE SUMMARY
# ============================================================

def get_quote_summary(
    ticker,
):
    """
    Retrieve only the modules required for the discovery
    eligibility test.

    Returns:
        result dictionary
        retrieved_at
        error
    """

    ticker = ticker.upper().strip()

    modules = (
        "price,"
        "financialData,"
        "defaultKeyStatistics,"
        "incomeStatementHistory"
    )

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        retrieved_at = datetime.now(
            timezone.utc
        )

        try:

            session, crumb = (
                create_yahoo_session()
            )

            url = (
                "https://query2.finance.yahoo.com/"
                "v10/finance/quoteSummary/"
                f"{ticker}"
            )

            response = session.get(
                url,
                params={
                    "modules": modules,
                    "crumb": crumb,
                    "formatted": "false",
                },
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            payload = response.json()

            quote_summary = payload.get(
                "quoteSummary",
                {}
            )

            error = quote_summary.get(
                "error"
            )

            if error:
                raise RuntimeError(
                    str(error)
                )

            results = quote_summary.get(
                "result"
            )

            if not results:
                raise RuntimeError(
                    "Yahoo returned no fundamentals result."
                )

            return (
                results[0],
                retrieved_at,
                None,
            )

        except Exception as exc:

            last_error = str(
                exc
            )

            if attempt < MAX_RETRIES:
                time.sleep(
                    0.5 * attempt
                )

    return (
        None,
        datetime.now(
            timezone.utc
        ),
        last_error,
    )


# ============================================================
# MARKET CAP
# ============================================================

def extract_market_cap(
    summary,
):
    """
    Prefer the price module's marketCap field.

    Fall back to defaultKeyStatistics if needed.
    """

    price = summary.get(
        "price",
        {}
    )

    market_cap = raw_value(
        price.get(
            "marketCap"
        )
    )

    if market_cap is not None:
        return market_cap

    stats = summary.get(
        "defaultKeyStatistics",
        {}
    )

    return raw_value(
        stats.get(
            "marketCap"
        )
    )


# ============================================================
# NET INCOME
# ============================================================

def extract_latest_net_income(
    summary,
):
    """
    Retrieve the latest annual Net Income from Yahoo's
    incomeStatementHistory module when available.
    """

    history = summary.get(
        "incomeStatementHistory",
        {}
    )

    statements = history.get(
        "incomeStatementHistory",
        []
    )

    if not statements:
        return None

    latest = statements[0]

    possible_fields = [
        "netIncome",
        "netIncomeApplicableToCommonShares",
        "netIncomeFromContinuingOps",
    ]

    for field_name in possible_fields:

        value = raw_value(
            latest.get(
                field_name
            )
        )

        if value is not None:
            return value

    return None


# ============================================================
# PROFITABILITY FALLBACKS
# ============================================================

def extract_profitability(
    summary,
):
    """
    Preferred:
        latest annual net income > 0

    Fallbacks:
        trailing EPS > 0
        profit margin > 0

    Returns:
        profitable
        net_income
        method
    """

    net_income = extract_latest_net_income(
        summary
    )

    if net_income is not None:

        return (
            net_income > 0,
            net_income,
            "latest annual net income",
        )

    stats = summary.get(
        "defaultKeyStatistics",
        {}
    )

    trailing_eps = raw_value(
        stats.get(
            "trailingEps"
        )
    )

    if trailing_eps is not None:

        return (
            trailing_eps > 0,
            None,
            "trailing EPS",
        )

    financial_data = summary.get(
        "financialData",
        {}
    )

    profit_margin = raw_value(
        financial_data.get(
            "profitMargins"
        )
    )

    if profit_margin is not None:

        return (
            profit_margin > 0,
            None,
            "profit margin",
        )

    return (
        None,
        None,
        None,
    )


# ============================================================
# ETF ELIGIBILITY
# ============================================================

def evaluate_etf_eligibility(
    ticker,
):

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
    v6.3.1 discovery eligibility:

    - approximately $10B+ market capitalization
    - profitable operating company

    Missing essential data => DATA INSUFFICIENT
    """

    (
        summary,
        retrieved_at,
        retrieval_error,
    ) = get_quote_summary(
        ticker
    )

    if summary is None:

        return EligibilityResult(
            ticker=ticker,

            eligible=False,

            status="DATA INSUFFICIENT",

            reason=(
                "Could not retrieve Yahoo fundamentals "
                "required for eligibility. "
                f"Retrieval error: {retrieval_error}"
            ),

            security_type="STOCK",

            market_cap=None,

            profitable=None,

            net_income=None,

            source=(
                "Yahoo Finance quoteSummary"
            ),

            retrieved_at=retrieved_at,
        )

    # --------------------------------------------------------
    # MARKET CAP
    # --------------------------------------------------------

    market_cap = extract_market_cap(
        summary
    )

    # --------------------------------------------------------
    # PROFITABILITY
    # --------------------------------------------------------

    (
        profitable,
        net_income,
        profitability_method,
    ) = extract_profitability(
        summary
    )

    # --------------------------------------------------------
    # DATA INSUFFICIENT
    # --------------------------------------------------------

    missing = []

    if market_cap is None:
        missing.append(
            "market capitalization"
        )

    if profitable is None:
        missing.append(
            "profitability evidence"
        )

    if missing:

        return EligibilityResult(
            ticker=ticker,

            eligible=False,

            status="DATA INSUFFICIENT",

            reason=(
                "Eligibility could not be established because "
                + " and ".join(
                    missing
                )
                + " were unavailable after retrieval."
            ),

            security_type="STOCK",

            market_cap=market_cap,

            profitable=profitable,

            net_income=net_income,

            source=(
                "Yahoo Finance quoteSummary"
            ),

            retrieved_at=retrieved_at,
        )

    # --------------------------------------------------------
    # MARKET-CAP TEST
    # --------------------------------------------------------

    if market_cap < MINIMUM_MARKET_CAP:

        return EligibilityResult(
            ticker=ticker,

            eligible=False,

            status="INELIGIBLE",

            reason=(
                f"Market capitalization "
                f"${market_cap / 1_000_000_000:.1f}B "
                "is below the approximately $10B "
                "v6.3.1 discovery threshold."
            ),

            security_type="STOCK",

            market_cap=market_cap,

            profitable=profitable,

            net_income=net_income,

            source=(
                "Yahoo Finance quoteSummary"
            ),

            retrieved_at=retrieved_at,
        )

    # --------------------------------------------------------
    # PROFITABILITY TEST
    # --------------------------------------------------------

    if not profitable:

        method_text = (
            profitability_method
            if profitability_method
            else "retrieved profitability data"
        )

        return EligibilityResult(
            ticker=ticker,

            eligible=False,

            status="INELIGIBLE",

            reason=(
                "The company does not satisfy the "
                "profitable-company requirement based on "
                f"{method_text}."
            ),

            security_type="STOCK",

            market_cap=market_cap,

            profitable=False,

            net_income=net_income,

            source=(
                "Yahoo Finance quoteSummary"
            ),

            retrieved_at=retrieved_at,
        )

    # --------------------------------------------------------
    # ELIGIBLE
    # --------------------------------------------------------

    method_text = (
        profitability_method
        if profitability_method
        else "retrieved profitability data"
    )

    return EligibilityResult(
        ticker=ticker,

        eligible=True,

        status="ELIGIBLE",

        reason=(
            f"Market capitalization "
            f"${market_cap / 1_000_000_000:.1f}B "
            "and positive profitability based on "
            f"{method_text} satisfy the v6.3.1 "
            "discovery eligibility requirements."
        ),

        security_type="STOCK",

        market_cap=market_cap,

        profitable=True,

        net_income=net_income,

        source=(
            "Yahoo Finance quoteSummary"
        ),

        retrieved_at=retrieved_at,
    )


# ============================================================
# MAIN ROUTER
# ============================================================

def evaluate_eligibility(
    ticker,
):

    ticker = ticker.upper().strip()

    if ticker in KNOWN_ETFS:

        return evaluate_etf_eligibility(
            ticker
        )

    return evaluate_stock_eligibility(
        ticker
    )
