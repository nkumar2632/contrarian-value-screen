import streamlit as st

from screening_engine import (
    GateResult,
    GateStatus,
    evaluate_gate_5,
    classify_candidate,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Contrarian Value Screen",
    page_icon="📉",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# SAMPLE SCREEN DATA
# ============================================================

# These are temporary sample records used to build and test
# the application architecture.
#
# They are NOT live market data and should not be treated
# as current investment analysis.

screen_data = {
    "run_date": "2026-09-01",
    "candidates": [
        {
            "ticker": "CMCSA",
            "company": "Comcast",
            "price": 31.20,
            "fair_value": 39.00,
            "downside_value": 25.00,
            "months_to_value": 12,
            "catalyst": (
                "Broadband stabilization and improving free cash flow."
            ),
            "bear_case": (
                "Continued broadband subscriber losses and "
                "weak cable economics."
            ),
        },
        {
            "ticker": "PYPL",
            "company": "PayPal",
            "price": 61.00,
            "fair_value": 75.00,
            "downside_value": 50.00,
            "months_to_value": 12,
            "catalyst": (
                "Margin improvement and renewed branded checkout growth."
            ),
            "bear_case": (
                "Competitive pressure and structurally slower "
                "transaction growth."
            ),
        },
        {
            "ticker": "ADBE",
            "company": "Adobe",
            "price": 291.52,
            "fair_value": 337.00,
            "downside_value": 200.00,
            "months_to_value": 12,
            "catalyst": (
                "AI monetization and stabilization of "
                "Creative Cloud growth."
            ),
            "bear_case": (
                "Generative AI competition pressures pricing and growth."
            ),
        },
    ],
}


# ============================================================
# RUN SCREENING ENGINE
# ============================================================

candidates = screen_data["candidates"]

for stock in candidates:

    gate_results = {}

    # --------------------------------------------------------
    # TEMPORARY GATE 1–4 PLACEHOLDERS
    # --------------------------------------------------------
    #
    # These PASS values exist ONLY to test the application flow.
    # They are not actual investment judgments.
    #
    # We will replace these with the precise v6.3.1 rules.

    for gate_number in range(1, 5):

        gate_results[gate_number] = GateResult(
            gate=gate_number,
            status=GateStatus.PASS,
            reason=(
                "Placeholder PASS until Gate "
                f"{gate_number} logic is implemented."
            ),
        )

    # --------------------------------------------------------
    # REAL GATE 5 CALCULATION
    # --------------------------------------------------------

    gate_results[5] = evaluate_gate_5(
        current_price=stock["price"],
        fair_value=stock["fair_value"],
        downside_value=stock["downside_value"],
        months_to_value=stock["months_to_value"],
    )

    stock["gate_results"] = gate_results

    # Overall classification

    stock["status"] = classify_candidate(gate_results)

    # Determine first failed gate

    stock["failed_gate"] = None

    for gate_number in range(1, 6):

        result = gate_results.get(gate_number)

        if result and result.status == GateStatus.FAIL:
            stock["failed_gate"] = gate_number
            break

    # Pull calculated Gate 5 metrics into the stock record

    gate_5_metrics = gate_results[5].metrics or {}

    stock["reward_downside"] = gate_5_metrics.get(
        "reward_downside"
    )

    stock["annualized_return"] = gate_5_metrics.get(
        "annualized_return"
    )

    # Use Gate 5 explanation for near-miss failure reason

    if gate_results[5].status == GateStatus.FAIL:
        stock["failure_reason"] = gate_results[5].reason

    elif gate_results[5].status == GateStatus.DATA_INSUFFICIENT:
        stock["failure_reason"] = gate_results[5].reason

    else:
        stock["failure_reason"] = None


# ============================================================
# DERIVED RESULTS
# ============================================================

survivors = [
    stock
    for stock in candidates
    if stock["status"] == "SURVIVOR"
]

near_misses = [
    stock
    for stock in candidates
    if stock["status"] == "NEAR MISS"
]

failed_candidates = [
    stock
    for stock in candidates
    if stock["status"] == "FAIL"
]

data_insufficient = [
    stock
    for stock in candidates
    if stock["status"] == "DATA INSUFFICIENT"
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_money(value):
    if value is None:
        return "N/A"

    return f"${value:,.2f}"


def format_ratio(value):
    if value is None:
        return "N/A"

    return f"{value:.2f}×"


def format_percent(value):
    if value is None:
        return "N/A"

    return f"{value:.1%}"


def display_stock_card(stock, headline):

    st.markdown(
        f"""
        <div class="ticker-card">
            <h3>{stock["ticker"]}</h3>
            <div class="company-name">
                {stock["company"]}
            </div>

            <p>
                <strong>{headline}</strong>
            </p>

            <p>
                <strong>Price:</strong>
                {format_money(stock["price"])}
            </p>

            <p>
                <strong>Fair value:</strong>
                {format_money(stock["fair_value"])}
            </p>

            <p>
                <strong>Downside:</strong>
                {format_money(stock["downside_value"])}
            </p>

            <p>
                <strong>Annualized return:</strong>
                {format_percent(stock["annualized_return"])}
            </p>

            <p>
                <strong>Reward / Downside:</strong>
                {format_ratio(stock["reward_downside"])}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def display_full_analysis(stock):

    with st.expander(
        f"View full {stock['ticker']} analysis"
    ):

        st.write(f"**Company:** {stock['company']}")

        st.write("### Gate Results")

        for gate_number in range(1, 6):

            result = stock["gate_results"][gate_number]

            st.write(
                f"**Gate {gate_number}: "
                f"{result.status.value}**"
            )

            st.caption(result.reason)

        st.write("### Valuation")

        st.write(
            f"**Current price:** "
            f"{format_money(stock['price'])}"
        )

        st.write(
            f"**Base fair value:** "
            f"{format_money(stock['fair_value'])}"
        )

        st.write(
            f"**Downside value:** "
            f"{format_money(stock['downside_value'])}"
        )

        st.write(
            f"**Time to value:** "
            f"{stock['months_to_value']} months"
        )

        st.write(
            f"**Annualized base return:** "
            f"{format_percent(stock['annualized_return'])}"
        )

        st.write(
            f"**Reward / downside:** "
            f"{format_ratio(stock['reward_downside'])}"
        )

        st.write("### Catalyst")

        st.write(stock["catalyst"])

        st.write("### Bear Case")

        st.write(stock["bear_case"])

        if stock["failure_reason"]:

            st.write("### Why It Failed")

            st.write(stock["failure_reason"])


# ============================================================
# MOBILE-FIRST CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 720px;
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        padding-bottom: 3rem;
    }

    .ticker-card {
        border: 1px solid rgba(128,128,128,0.30);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 10px;
    }

    .ticker-card h3 {
        margin-top: 0;
        margin-bottom: 2px;
    }

    .company-name {
        opacity: 0.65;
        margin-bottom: 12px;
    }

    .ticker-card p {
        margin-top: 7px;
        margin-bottom: 7px;
    }

    div.stButton > button {
        width: 100%;
        min-height: 48px;
        font-size: 1rem;
        border-radius: 12px;
    }

    @media (max-width: 600px) {

        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }

        h1 {
            font-size: 2rem !important;
        }

        h2 {
            font-size: 1.5rem !important;
        }

        .ticker-card {
            padding: 14px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.title("Contrarian Value Screen")

st.caption(
    "6–18 month value + catalyst opportunities"
)


# ============================================================
# SUMMARY
# ============================================================

col1, col2, col3 = st.columns(3)

col1.metric(
    "Candidates",
    len(candidates),
)

col2.metric(
    "Survivors",
    len(survivors),
)

col3.metric(
    "Near Misses",
    len(near_misses),
)


# ============================================================
# RUN BUTTON
# ============================================================

if st.button(
    "Run New Screen",
    use_container_width=True,
):

    st.info(
        "The live screening workflow will be connected "
        "in a later step."
    )


# ============================================================
# SURVIVORS
# ============================================================

st.divider()

st.subheader("Survivors")

if not survivors:

    st.write(
        "No candidates passed all five gates."
    )

for stock in survivors:

    display_stock_card(
        stock,
        "PASS — All Gates",
    )

    display_full_analysis(stock)


# ============================================================
# NEAR MISSES
# ============================================================

st.divider()

st.subheader("Near Misses")

if not near_misses:

    st.write(
        "No Gate 5 near misses."
    )

for stock in near_misses:

    failed_gate = stock["failed_gate"]

    headline = (
        f"Gate {failed_gate} FAIL"
        if failed_gate
        else "NEAR MISS"
    )

    display_stock_card(
        stock,
        headline,
    )

    display_full_analysis(stock)


# ============================================================
# FAILED CANDIDATES
# ============================================================

if failed_candidates:

    st.divider()

    st.subheader("Failed Candidates")

    for stock in failed_candidates:

        failed_gate = stock["failed_gate"]

        headline = (
            f"Gate {failed_gate} FAIL"
            if failed_gate
            else "FAIL"
        )

        display_stock_card(
            stock,
            headline,
        )

        display_full_analysis(stock)


# ============================================================
# DATA INSUFFICIENT
# ============================================================

if data_insufficient:

    st.divider()

    st.subheader("Data Insufficient")

    for stock in data_insufficient:

        display_stock_card(
            stock,
            "DATA INSUFFICIENT",
        )

        display_full_analysis(stock)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    f"Screen date: {screen_data['run_date']}"
)

st.caption(
    "Development version — sample data only. "
    "Gate 1–4 logic has not yet been implemented."
)
