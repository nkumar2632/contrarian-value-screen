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
# SAMPLE DATA
# ============================================================

# DEVELOPMENT DATA ONLY
# These are temporary sample values used to test the app.
# They are NOT live market data.

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
# HELPER FUNCTIONS
# ============================================================

def format_money(value):
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_percent(value):
    if value is None:
        return "N/A"
    return f"{value:.1%}"


def format_ratio(value):
    if value is None:
        return "N/A"
    return f"{value:.2f}×"


def gate_icon(status):
    if status == GateStatus.PASS:
        return "✅"

    if status == GateStatus.FAIL:
        return "❌"

    if status == GateStatus.DATA_INSUFFICIENT:
        return "⚠️"

    return "➖"


# ============================================================
# SCREENING ENGINE
# ============================================================

candidates = screen_data["candidates"]

for stock in candidates:

    gate_results = {}

    # --------------------------------------------------------
    # GATES 1–4
    # --------------------------------------------------------
    # TEMPORARY DEVELOPMENT PLACEHOLDERS ONLY.
    #
    # These are NOT actual investment conclusions.
    # They will be replaced with the exact v6.3.1 rules.

    for gate_number in range(1, 5):

        gate_results[gate_number] = GateResult(
            gate=gate_number,
            status=GateStatus.PASS,
            reason=(
                f"Development placeholder. "
                f"Gate {gate_number} logic not yet implemented."
            ),
        )

    # --------------------------------------------------------
    # GATE 5
    # --------------------------------------------------------

    gate_results[5] = evaluate_gate_5(
        current_price=stock["price"],
        fair_value=stock["fair_value"],
        downside_value=stock["downside_value"],
        months_to_value=stock["months_to_value"],
    )

    stock["gate_results"] = gate_results

    # --------------------------------------------------------
    # FINAL CLASSIFICATION
    # --------------------------------------------------------

    stock["status"] = classify_candidate(gate_results)

    stock["failed_gate"] = None

    for gate_number in range(1, 6):

        result = gate_results[gate_number]

        if result.status == GateStatus.FAIL:
            stock["failed_gate"] = gate_number
            break

    # --------------------------------------------------------
    # GATE 5 METRICS
    # --------------------------------------------------------

    gate_5_metrics = gate_results[5].metrics or {}

    stock["annualized_return"] = gate_5_metrics.get(
        "annualized_return"
    )

    stock["reward_downside"] = gate_5_metrics.get(
        "reward_downside"
    )

    stock["failure_reason"] = None

    if gate_results[5].status in {
        GateStatus.FAIL,
        GateStatus.DATA_INSUFFICIENT,
    }:
        stock["failure_reason"] = gate_results[5].reason


# ============================================================
# RESULT GROUPS
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
# MOBILE-FRIENDLY STYLING
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

        h3 {
            font-size: 1.25rem !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DISPLAY FUNCTIONS
# ============================================================

def display_stock_card(stock):

    with st.container(border=True):

        st.subheader(stock["ticker"])

        st.caption(stock["company"])

        if stock["status"] == "SURVIVOR":
            st.success("PASS — All 5 Gates")

        elif stock["status"] == "NEAR MISS":
            st.error(
                f"Gate {stock['failed_gate']} FAIL — Near Miss"
            )

        elif stock["status"] == "FAIL":
            st.error(
                f"Gate {stock['failed_gate']} FAIL"
            )

        elif stock["status"] == "DATA INSUFFICIENT":
            st.warning("DATA INSUFFICIENT")

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Price",
                format_money(stock["price"]),
            )

            st.metric(
                "Downside",
                format_money(stock["downside_value"]),
            )

        with col2:

            st.metric(
                "Fair Value",
                format_money(stock["fair_value"]),
            )

            st.metric(
                "Reward / Downside",
                format_ratio(stock["reward_downside"]),
            )

        st.metric(
            "Annualized Base Return",
            format_percent(stock["annualized_return"]),
        )

        with st.expander(
            f"View full {stock['ticker']} analysis"
        ):

            st.markdown("### Gate Results")

            for gate_number in range(1, 6):

                result = stock["gate_results"][gate_number]

                st.write(
                    f"{gate_icon(result.status)} "
                    f"**Gate {gate_number}: "
                    f"{result.status.value}**"
                )

                st.caption(result.reason)

            st.markdown("### Valuation")

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
                f"**Annualized return:** "
                f"{format_percent(stock['annualized_return'])}"
            )

            st.write(
                f"**Reward / downside:** "
                f"{format_ratio(stock['reward_downside'])}"
            )

            st.markdown("### Catalyst")

            st.write(stock["catalyst"])

            st.markdown("### Bear Case")

            st.write(stock["bear_case"])

            if stock["failure_reason"]:

                st.markdown("### Why It Failed")

                st.write(stock["failure_reason"])


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
        "Live screening is not connected yet. "
        "The current screen uses development sample data."
    )


# ============================================================
# SURVIVORS
# ============================================================

st.divider()

st.header("Survivors")

if not survivors:

    st.info(
        "No candidates passed all five gates."
    )

else:

    for stock in survivors:
        display_stock_card(stock)


# ============================================================
# NEAR MISSES
# ============================================================

st.divider()

st.header("Near Misses")

if not near_misses:

    st.write(
        "No Gate 5 near misses."
    )

else:

    for stock in near_misses:
        display_stock_card(stock)


# ============================================================
# FAILED CANDIDATES
# ============================================================

if failed_candidates:

    st.divider()

    st.header("Failed Candidates")

    for stock in failed_candidates:
        display_stock_card(stock)


# ============================================================
# DATA INSUFFICIENT
# ============================================================

if data_insufficient:

    st.divider()

    st.header("Data Insufficient")

    for stock in data_insufficient:
        display_stock_card(stock)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    f"Screen date: {screen_data['run_date']}"
)

st.caption(
    "Development version — sample data only."
)

st.caption(
    "Gate 1–4 results are temporary placeholders. "
    "Gate 5 is calculated by screening_engine.py."
)
