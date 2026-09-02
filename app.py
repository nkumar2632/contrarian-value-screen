import streamlit as st

from data_sources import get_yahoo_price

from screening_engine import (
    Gate1Input,
    Gate2Input,
    Gate3Input,
    Gate4Input,
    Gate5Input,
    GateStatus,
    CandidateStatus,
    evaluate_gate_1,
    evaluate_gate_2,
    evaluate_gate_3,
    evaluate_gate_4,
    evaluate_gate_5,
    classify_candidate,
    first_failed_gate,
    gate_5_recheck_price,
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
# LIVE PRICE CACHE
# ============================================================

@st.cache_data(ttl=300)
def retrieve_price(ticker):
    """
    Cache live market retrieval for 5 minutes so Streamlit
    reruns do not repeatedly query the source.
    """
    return get_yahoo_price(ticker)


# ============================================================
# DEVELOPMENT SCREEN DATA
# ============================================================

# IMPORTANT:
#
# Current prices are retrieved live.
#
# Gate 1–4 evidence and Gate 5 valuation assumptions below
# remain DEVELOPMENT FIXTURES. They are not yet based on the
# complete live v6.3.1 research workflow.

screen_data = {
    "candidates": [
        {
            "ticker": "CMCSA",
            "company": "Comcast",

            "entry_reason": (
                "Development candidate used to test the "
                "v6.3.1 screening workflow."
            ),

            "gate1": Gate1Input(
                valuation_method_1="Forward P/E vs own history",
                valuation_result_1="Development fixture: discounted",
                valuation_method_2="FCF yield vs peers",
                valuation_result_2="Development fixture: discounted",
                check_1_supports_undervaluation=True,
                check_2_supports_undervaluation=True,
                methods_materially_contradict=False,
            ),

            "gate2": Gate2Input(
                mispricing_mechanism=(
                    "Development fixture: market may be extrapolating "
                    "broadband weakness too aggressively."
                ),
                economic_explanation=(
                    "If subscriber losses stabilize while free cash "
                    "flow remains resilient, normalized economics "
                    "could be stronger than implied."
                ),
                mechanism_supported=True,
            ),

            "gate3": Gate3Input(
                strongest_bear_case=(
                    "Broadband could face structural deterioration "
                    "from fixed-wireless competition."
                ),
                structural_impairment_sufficient=False,
                unresolved_structural_risks=[
                    "Broadband competition",
                    "Long-term cable economics",
                ],
            ),

            "gate4": Gate4Input(
                catalyst=(
                    "Broadband stabilization and improving "
                    "free cash flow."
                ),
                economic_link=(
                    "Improved operating durability could affect "
                    "earnings expectations and valuation."
                ),
                timing_months=12,
                catalyst_supported=True,
            ),

            "gate5": Gate5Input(
                current_price=None,
                base_operating_assumption=(
                    "Development fixture: free cash flow remains "
                    "resilient while broadband trends stabilize."
                ),
                fair_value_low=39.00,
                fair_value_high=43.00,
                conservative_fair_value=39.00,
                fair_value_basis=(
                    "Development fixture: conservative normalized "
                    "valuation range."
                ),
                adverse_operating_assumption=(
                    "Broadband weakness persists and normalized "
                    "valuation remains depressed."
                ),
                downside_low=25.00,
                downside_high=28.00,
                conservative_downside=25.00,
                downside_basis=(
                    "Development fixture: adverse operating scenario."
                ),
                months_to_value=12,
            ),
        },

        {
            "ticker": "PYPL",
            "company": "PayPal",

            "entry_reason": (
                "Development candidate used to test the "
                "v6.3.1 screening workflow."
            ),

            "gate1": Gate1Input(
                valuation_method_1="Forward P/E vs own history",
                valuation_result_1="Development fixture: discounted",
                valuation_method_2="Free-cash-flow yield",
                valuation_result_2="Development fixture: discounted",
                check_1_supports_undervaluation=True,
                check_2_supports_undervaluation=True,
                methods_materially_contradict=False,
            ),

            "gate2": Gate2Input(
                mispricing_mechanism=(
                    "Development fixture: market may be "
                    "over-discounting slower branded checkout growth."
                ),
                economic_explanation=(
                    "Margin improvement and execution could produce "
                    "better normalized economics than implied."
                ),
                mechanism_supported=True,
            ),

            "gate3": Gate3Input(
                strongest_bear_case=(
                    "Competitive pressure may represent permanent "
                    "erosion of PayPal's economics."
                ),
                structural_impairment_sufficient=False,
                unresolved_structural_risks=[
                    "Checkout competition",
                    "Take-rate pressure",
                ],
            ),

            "gate4": Gate4Input(
                catalyst=(
                    "Margin improvement and renewed branded "
                    "checkout growth."
                ),
                economic_link=(
                    "Better growth and margins would increase "
                    "normalized earnings and cash flow."
                ),
                timing_months=12,
                catalyst_supported=True,
            ),

            "gate5": Gate5Input(
                current_price=None,
                base_operating_assumption=(
                    "Development fixture: margins improve and "
                    "branded checkout growth stabilizes."
                ),
                fair_value_low=75.00,
                fair_value_high=82.00,
                conservative_fair_value=75.00,
                fair_value_basis=(
                    "Development fixture: normalized earnings "
                    "valuation range."
                ),
                adverse_operating_assumption=(
                    "Growth remains weak and competitive pressure "
                    "persists."
                ),
                downside_low=50.00,
                downside_high=54.00,
                conservative_downside=50.00,
                downside_basis=(
                    "Development fixture: adverse competitive "
                    "scenario."
                ),
                months_to_value=12,
            ),
        },

        {
            "ticker": "ADBE",
            "company": "Adobe",

            "entry_reason": (
                "Development candidate used to test the "
                "v6.3.1 screening workflow."
            ),

            "gate1": Gate1Input(
                valuation_method_1="Forward P/E vs own history",
                valuation_result_1="Development fixture: discounted",
                valuation_method_2="Free-cash-flow yield",
                valuation_result_2="Development fixture: discounted",
                check_1_supports_undervaluation=True,
                check_2_supports_undervaluation=True,
                methods_materially_contradict=False,
            ),

            "gate2": Gate2Input(
                mispricing_mechanism=(
                    "Development fixture: market may be pricing "
                    "excessive disruption from generative AI."
                ),
                economic_explanation=(
                    "If Adobe monetizes AI while protecting its "
                    "installed base, current expectations could "
                    "prove too pessimistic."
                ),
                mechanism_supported=True,
            ),

            "gate3": Gate3Input(
                strongest_bear_case=(
                    "Generative AI could structurally weaken Adobe's "
                    "pricing power and competitive moat."
                ),
                structural_impairment_sufficient=False,
                unresolved_structural_risks=[
                    "AI disruption",
                    "Pricing pressure",
                ],
            ),

            "gate4": Gate4Input(
                catalyst=(
                    "AI monetization and stabilization of "
                    "Creative Cloud growth."
                ),
                economic_link=(
                    "Successful monetization could improve earnings "
                    "growth and investor expectations."
                ),
                timing_months=12,
                catalyst_supported=True,
            ),

            "gate5": Gate5Input(
                current_price=None,
                base_operating_assumption=(
                    "Development fixture: Creative Cloud growth "
                    "stabilizes and AI contributes incrementally."
                ),
                fair_value_low=337.00,
                fair_value_high=360.00,
                conservative_fair_value=337.00,
                fair_value_basis=(
                    "Development fixture: normalized earnings "
                    "valuation range."
                ),
                adverse_operating_assumption=(
                    "AI competition pressures growth and valuation."
                ),
                downside_low=200.00,
                downside_high=225.00,
                conservative_downside=200.00,
                downside_basis=(
                    "Development fixture: adverse structural "
                    "AI scenario."
                ),
                months_to_value=12,
            ),
        },
    ]
}


# ============================================================
# FORMATTING
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


def format_datetime(value):
    if value is None:
        return "N/A"

    return value.strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def gate_icon(status):
    if status == GateStatus.PASS:
        return "✅"

    if status == GateStatus.FAIL:
        return "❌"

    if status == GateStatus.DATA_INSUFFICIENT:
        return "⚠️"

    return "➖"


# ============================================================
# RETRIEVE LIVE PRICES
# ============================================================

for stock in screen_data["candidates"]:

    price_result = retrieve_price(
        stock["ticker"]
    )

    stock["price_result"] = price_result

    # Never fall back silently to a remembered or
    # previously hard-coded price.
    stock["gate5"].current_price = (
        price_result.price
        if price_result.error is None
        else None
    )


# ============================================================
# RUN SEQUENTIAL GATES
# ============================================================

for stock in screen_data["candidates"]:

    results = {}

    # Gate 1

    results[1] = evaluate_gate_1(
        stock["gate1"]
    )

    # Gate 2

    if results[1].status == GateStatus.PASS:

        results[2] = evaluate_gate_2(
            stock["gate2"]
        )

    else:
        results[2] = None

    # Gate 3

    if (
        results[2]
        and results[2].status == GateStatus.PASS
    ):

        results[3] = evaluate_gate_3(
            stock["gate3"]
        )

    else:
        results[3] = None

    # Gate 4

    if (
        results[3]
        and results[3].status == GateStatus.PASS
    ):

        results[4] = evaluate_gate_4(
            stock["gate4"]
        )

    else:
        results[4] = None

    # Gate 5

    if (
        results[4]
        and results[4].status == GateStatus.PASS
    ):

        results[5] = evaluate_gate_5(
            stock["gate5"]
        )

    else:
        results[5] = None

    stock["gate_results"] = results

    completed_results = {
        gate_number: result
        for gate_number, result in results.items()
        if result is not None
    }

    stock["status"] = classify_candidate(
        completed_results
    )

    stock["failed_gate"] = first_failed_gate(
        completed_results
    )

    # ----------------------------------------
    # Gate 5 metrics
    # ----------------------------------------

    if results[5] is not None:

        metrics = results[5].metrics

        stock["price"] = metrics.get(
            "current_price"
        )

        stock["fair_value"] = metrics.get(
            "conservative_fair_value"
        )

        stock["downside_value"] = metrics.get(
            "conservative_downside"
        )

        stock["annualized_return"] = metrics.get(
            "annualized_return"
        )

        stock["reward_downside"] = metrics.get(
            "reward_downside"
        )

        stock["upside_percent"] = metrics.get(
            "upside_percent"
        )

        stock["downside_percent"] = metrics.get(
            "downside_percent"
        )

    else:

        stock["price"] = (
            stock["price_result"].price
        )

        stock["fair_value"] = None
        stock["downside_value"] = None
        stock["annualized_return"] = None
        stock["reward_downside"] = None
        stock["upside_percent"] = None
        stock["downside_percent"] = None

    # ----------------------------------------
    # Near-miss price
    # ----------------------------------------

    stock["recheck"] = None

    if (
        results[5]
        and results[5].status == GateStatus.FAIL
    ):

        stock["recheck"] = (
            gate_5_recheck_price(
                fair_value=(
                    stock["gate5"]
                    .conservative_fair_value
                ),
                downside_value=(
                    stock["gate5"]
                    .conservative_downside
                ),
                months_to_value=(
                    stock["gate5"]
                    .months_to_value
                ),
            )
        )


# ============================================================
# GROUP RESULTS
# ============================================================

candidates = screen_data["candidates"]

survivors = [
    stock
    for stock in candidates
    if stock["status"]
    == CandidateStatus.SURVIVOR
]

near_misses = [
    stock
    for stock in candidates
    if stock["status"]
    == CandidateStatus.NEAR_MISS
]

failed_candidates = [
    stock
    for stock in candidates
    if stock["status"]
    == CandidateStatus.FAIL
]

data_insufficient = [
    stock
    for stock in candidates
    if stock["status"]
    == CandidateStatus.DATA_INSUFFICIENT
]


# ============================================================
# CSS
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
# DISPLAY HELPERS
# ============================================================

def display_price_source(stock):

    result = stock["price_result"]

    if result.error:

        st.error(
            "Live price retrieval failed."
        )

        st.caption(
            result.error
        )

        return

    st.caption(
        "Price source: "
        f"{result.source}"
    )

    st.caption(
        "Market timestamp: "
        f"{format_datetime(result.market_time)}"
    )

    st.caption(
        "Retrieved: "
        f"{format_datetime(result.retrieved_at)}"
    )

    st.markdown(
        f"[Open retrieved price source]"
        f"({result.source_url})"
    )


def display_gate_result(
    gate_number,
    result,
):

    if result is None:

        st.write(
            f"➖ **Gate {gate_number}: "
            "NOT EVALUATED**"
        )

        st.caption(
            "Evaluation stopped because an earlier "
            "gate did not pass."
        )

        return

    st.write(
        f"{gate_icon(result.status)} "
        f"**Gate {gate_number}: "
        f"{result.status.value}**"
    )

    st.caption(
        result.reason
    )


def display_stock(stock):

    with st.container(border=True):

        st.subheader(
            stock["ticker"]
        )

        st.caption(
            stock["company"]
        )

        # ----------------------------------------
        # Status
        # ----------------------------------------

        if (
            stock["status"]
            == CandidateStatus.SURVIVOR
        ):

            st.success(
                "SURVIVOR — Passed all 5 gates"
            )

        elif (
            stock["status"]
            == CandidateStatus.NEAR_MISS
        ):

            st.error(
                f"Gate {stock['failed_gate']} "
                "FAIL — Near Miss"
            )

        elif (
            stock["status"]
            == CandidateStatus.FAIL
        ):

            st.error(
                f"Gate {stock['failed_gate']} FAIL"
            )

        elif (
            stock["status"]
            == CandidateStatus.DATA_INSUFFICIENT
        ):

            st.warning(
                "DATA INSUFFICIENT — retrieval attempted"
            )

        else:

            st.warning(
                "NOT FULLY EVALUATED"
            )

        # ----------------------------------------
        # Price
        # ----------------------------------------

        st.metric(
            "Current Retrieved Price",
            format_money(
                stock["price_result"].price
            ),
        )

        display_price_source(
            stock
        )

        # ----------------------------------------
        # Gate 5 metrics
        # ----------------------------------------

        if stock["gate_results"][5]:

            st.divider()

            col1, col2 = st.columns(2)

            col1.metric(
                "Fair Value",
                format_money(
                    stock["fair_value"]
                ),
            )

            col2.metric(
                "Downside Value",
                format_money(
                    stock["downside_value"]
                ),
            )

            col1.metric(
                "Upside",
                format_percent(
                    stock["upside_percent"]
                ),
            )

            col2.metric(
                "Downside",
                format_percent(
                    stock["downside_percent"]
                ),
            )

            st.metric(
                "Reward / Downside",
                format_ratio(
                    stock["reward_downside"]
                ),
            )

            st.metric(
                "Annualized Base Return",
                format_percent(
                    stock["annualized_return"]
                ),
            )

        # ----------------------------------------
        # Full analysis
        # ----------------------------------------

        with st.expander(
            f"View full {stock['ticker']} analysis"
        ):

            st.markdown(
                "### Gate Results"
            )

            for gate_number in range(1, 6):

                display_gate_result(
                    gate_number,
                    stock["gate_results"].get(
                        gate_number
                    ),
                )

            st.markdown(
                "### Price Integrity"
            )

            display_price_source(
                stock
            )

            if stock["gate_results"][5]:

                st.markdown(
                    "### Gate 5 Valuation"
                )

                st.write(
                    "**Base operating assumption:** "
                    + stock[
                        "gate5"
                    ].base_operating_assumption
                )

                st.write(
                    "**Fair-value range:** "
                    f"{format_money(stock['gate5'].fair_value_low)} "
                    "to "
                    f"{format_money(stock['gate5'].fair_value_high)}"
                )

                st.write(
                    "**Conservative fair value used:** "
                    f"{format_money(stock['gate5'].conservative_fair_value)}"
                )

                st.write(
                    "**Fair-value basis:** "
                    + stock[
                        "gate5"
                    ].fair_value_basis
                )

                st.write(
                    "**Adverse operating assumption:** "
                    + stock[
                        "gate5"
                    ].adverse_operating_assumption
                )

                st.write(
                    "**Downside range:** "
                    f"{format_money(stock['gate5'].downside_low)} "
                    "to "
                    f"{format_money(stock['gate5'].downside_high)}"
                )

                st.write(
                    "**Conservative downside used:** "
                    f"{format_money(stock['gate5'].conservative_downside)}"
                )

                st.write(
                    "**Downside basis:** "
                    + stock[
                        "gate5"
                    ].downside_basis
                )

                st.write(
                    "**Upside:** "
                    f"{format_percent(stock['upside_percent'])}"
                )

                st.write(
                    "**Downside:** "
                    f"{format_percent(stock['downside_percent'])}"
                )

                st.write(
                    "**Reward / downside:** "
                    f"{format_ratio(stock['reward_downside'])}"
                )

                st.write(
                    "**Annualized base return:** "
                    f"{format_percent(stock['annualized_return'])}"
                )

            if stock["recheck"]:

                st.markdown(
                    "### Near-Miss Recheck"
                )

                st.write(
                    "Maximum approximate share price "
                    "that would satisfy both existing "
                    "Gate 5 hurdles without changing "
                    "fair-value or downside assumptions:"
                )

                st.metric(
                    "Recheck Price",
                    format_money(
                        stock["recheck"][
                            "qualifying_price"
                        ]
                    ),
                )

                st.caption(
                    "Binding hurdle: "
                    + stock["recheck"][
                        "binding_constraint"
                    ]
                )


# ============================================================
# HEADER
# ============================================================

st.title(
    "Contrarian Value Screen"
)

st.caption(
    "v6.3.1 — 6–18 month value + catalyst screen"
)


# ============================================================
# DEVELOPMENT WARNING
# ============================================================

st.warning(
    "LIVE PRICE TEST: current prices are now retrieved "
    "from Yahoo Finance. Candidate selection, Gate 1–4 "
    "evidence, fair values, and downside assumptions "
    "remain development fixtures and are NOT current "
    "investment conclusions."
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
# REFRESH BUTTON
# ============================================================

if st.button(
    "Refresh Live Prices",
    use_container_width=True,
):

    retrieve_price.clear()

    st.rerun()


# ============================================================
# INITIAL CANDIDATE LIST
# ============================================================

st.divider()

st.header(
    "Initial Candidate List"
)

for stock in candidates:

    st.write(
        f"**{stock['ticker']} — "
        f"{stock['company']}**"
    )

    st.caption(
        stock["entry_reason"]
    )


# ============================================================
# DATA INSUFFICIENT
# ============================================================

st.divider()

st.header(
    "Data-Insufficient Candidates"
)

if not data_insufficient:

    st.write(
        "None."
    )

else:

    for stock in data_insufficient:
        display_stock(stock)


# ============================================================
# ELIMINATIONS
# ============================================================

st.divider()

st.header(
    "Eliminations"
)

if not failed_candidates:

    st.write(
        "No Gate 1–4 eliminations."
    )

else:

    for stock in failed_candidates:
        display_stock(stock)


# ============================================================
# SURVIVORS
# ============================================================

st.divider()

st.header(
    "Survivors"
)

if not survivors:

    st.info(
        "No candidates passed all five gates."
    )

else:

    for stock in survivors:
        display_stock(stock)


# ============================================================
# NEAR MISSES
# ============================================================

st.divider()

st.header(
    "Near-Miss Recheck List"
)

if not near_misses:

    st.write(
        "None."
    )

else:

    for stock in near_misses:
        display_stock(stock)


# ============================================================
# SURVIVOR RANKING
# ============================================================

st.divider()

st.header(
    "Survivor Ranking"
)

if not survivors:

    st.write(
        "There is no survivor ranking."
    )

else:

    st.write(
        "Ranking will be activated once the live "
        "research layer is connected."
    )


# ============================================================
# DISCIPLINE CHECK
# ============================================================

st.divider()

st.header(
    "Discipline Check"
)

if not survivors:

    st.write(
        "There is no #1 survivor."
    )

else:

    st.write(
        "The final independent recommendation check "
        "will be performed once live evidence retrieval "
        "is connected."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Development build — v6.3.1 engine with "
    "live market-price retrieval."
)
