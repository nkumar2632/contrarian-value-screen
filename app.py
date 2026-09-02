import streamlit as st

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
# SAMPLE DEVELOPMENT DATA
# ============================================================

# These are placeholder inputs to test the v6.3.1 engine.
# They are NOT live market data and NOT investment conclusions.

screen_data = {
    "run_date": "2026-09-01",
    "candidates": [
        {
            "ticker": "CMCSA",
            "company": "Comcast",

            "gate1": Gate1Input(
                valuation_method_1="Forward P/E vs own history",
                valuation_result_1="Appears discounted",
                valuation_method_2="FCF yield vs peers",
                valuation_result_2="Appears discounted",
                check_1_supports_undervaluation=True,
                check_2_supports_undervaluation=True,
                methods_materially_contradict=False,
            ),

            "gate2": Gate2Input(
                mispricing_mechanism=(
                    "Market may be extrapolating broadband weakness "
                    "too aggressively."
                ),
                economic_explanation=(
                    "If subscriber losses stabilize while free cash "
                    "flow remains resilient, current valuation may "
                    "understate normalized economics."
                ),
                mechanism_supported=True,
            ),

            "gate3": Gate3Input(
                strongest_bear_case=(
                    "Broadband may be in structural decline because "
                    "of fixed-wireless competition."
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
                    "Stabilization could improve earnings durability "
                    "and investor expectations."
                ),
                timing_months=12,
                catalyst_supported=True,
            ),

            "gate5": Gate5Input(
                current_price=31.20,
                base_operating_assumption=(
                    "Free cash flow remains resilient while broadband "
                    "trends stabilize."
                ),
                fair_value_low=39.00,
                fair_value_high=43.00,
                conservative_fair_value=39.00,
                fair_value_basis=(
                    "Conservative end of reasonable normalized "
                    "valuation range."
                ),
                adverse_operating_assumption=(
                    "Broadband losses remain elevated and valuation "
                    "compresses."
                ),
                downside_low=25.00,
                downside_high=28.00,
                conservative_downside=25.00,
                downside_basis=(
                    "Conservative valuation under continued "
                    "operating weakness."
                ),
                months_to_value=12,
            ),
        },

        {
            "ticker": "PYPL",
            "company": "PayPal",

            "gate1": Gate1Input(
                valuation_method_1="Forward P/E vs own history",
                valuation_result_1="Appears discounted",
                valuation_method_2="FCF yield",
                valuation_result_2="Appears discounted",
                check_1_supports_undervaluation=True,
                check_2_supports_undervaluation=True,
                methods_materially_contradict=False,
            ),

            "gate2": Gate2Input(
                mispricing_mechanism=(
                    "Market may be over-discounting slower branded "
                    "checkout growth."
                ),
                economic_explanation=(
                    "Margin improvement and execution could produce "
                    "better earnings growth than currently expected."
                ),
                mechanism_supported=True,
            ),

            "gate3": Gate3Input(
                strongest_bear_case=(
                    "Competitive pressure may represent a permanent "
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
                    "Margin improvement and renewed branded checkout "
                    "growth."
                ),
                economic_link=(
                    "Improved growth and margins would raise normalized "
                    "earnings and cash flow."
                ),
                timing_months=12,
                catalyst_supported=True,
            ),

            "gate5": Gate5Input(
                current_price=61.00,
                base_operating_assumption=(
                    "Margins improve and branded checkout growth "
                    "stabilizes."
                ),
                fair_value_low=75.00,
                fair_value_high=82.00,
                conservative_fair_value=75.00,
                fair_value_basis=(
                    "Conservative normalized earnings valuation."
                ),
                adverse_operating_assumption=(
                    "Growth remains weak and competitive pressure "
                    "persists."
                ),
                downside_low=50.00,
                downside_high=54.00,
                conservative_downside=50.00,
                downside_basis=(
                    "Lower normalized valuation under sustained "
                    "competitive pressure."
                ),
                months_to_value=12,
            ),
        },

        {
            "ticker": "ADBE",
            "company": "Adobe",

            "gate1": Gate1Input(
                valuation_method_1="Forward P/E vs own history",
                valuation_result_1="Appears discounted",
                valuation_method_2="FCF yield",
                valuation_result_2="Appears discounted",
                check_1_supports_undervaluation=True,
                check_2_supports_undervaluation=True,
                methods_materially_contradict=False,
            ),

            "gate2": Gate2Input(
                mispricing_mechanism=(
                    "Market may be pricing excessive disruption from "
                    "generative AI."
                ),
                economic_explanation=(
                    "If Adobe monetizes AI while protecting its "
                    "installed base, current expectations may prove "
                    "too pessimistic."
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
                    "AI monetization and stabilization of Creative "
                    "Cloud growth."
                ),
                economic_link=(
                    "Successful AI monetization could support earnings "
                    "growth and improve investor expectations."
                ),
                timing_months=12,
                catalyst_supported=True,
            ),

            "gate5": Gate5Input(
                current_price=291.52,
                base_operating_assumption=(
                    "Creative Cloud growth stabilizes and AI products "
                    "contribute incrementally."
                ),
                fair_value_low=337.00,
                fair_value_high=360.00,
                conservative_fair_value=337.00,
                fair_value_basis=(
                    "Conservative normalized earnings valuation."
                ),
                adverse_operating_assumption=(
                    "AI competition pressures growth and multiple."
                ),
                downside_low=200.00,
                downside_high=225.00,
                conservative_downside=200.00,
                downside_basis=(
                    "Lower earnings expectations and compressed "
                    "valuation under structural AI pressure."
                ),
                months_to_value=12,
            ),
        },
    ],
}


# ============================================================
# FORMATTING HELPERS
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
# RUN THE SCREEN
# ============================================================

for stock in screen_data["candidates"]:

    gate_results = {}

    gate_results[1] = evaluate_gate_1(
        stock["gate1"]
    )

    if gate_results[1].status == GateStatus.PASS:
        gate_results[2] = evaluate_gate_2(
            stock["gate2"]
        )
    else:
        gate_results[2] = None

    if (
        gate_results[2]
        and gate_results[2].status == GateStatus.PASS
    ):
        gate_results[3] = evaluate_gate_3(
            stock["gate3"]
        )
    else:
        gate_results[3] = None

    if (
        gate_results[3]
        and gate_results[3].status == GateStatus.PASS
    ):
        gate_results[4] = evaluate_gate_4(
            stock["gate4"]
        )
    else:
        gate_results[4] = None

    if (
        gate_results[4]
        and gate_results[4].status == GateStatus.PASS
    ):
        gate_results[5] = evaluate_gate_5(
            stock["gate5"]
        )
    else:
        gate_results[5] = None

    stock["gate_results"] = gate_results

    # Build classification-compatible gate dict
    completed_gates = {
        gate_number: result
        for gate_number, result in gate_results.items()
        if result is not None
    }

    stock["status"] = classify_candidate(
        completed_gates
    )

    stock["failed_gate"] = first_failed_gate(
        completed_gates
    )

    if gate_results[5]:

        metrics = gate_results[5].metrics

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

        stock["price"] = stock["gate5"].current_price
        stock["fair_value"] = None
        stock["downside_value"] = None
        stock["annualized_return"] = None
        stock["reward_downside"] = None
        stock["upside_percent"] = None
        stock["downside_percent"] = None

    # Gate 5 recheck price
    stock["recheck"] = None

    if (
        gate_results[5]
        and gate_results[5].status == GateStatus.FAIL
    ):

        stock["recheck"] = gate_5_recheck_price(
            fair_value=stock["gate5"].conservative_fair_value,
            downside_value=stock["gate5"].conservative_downside,
            months_to_value=stock["gate5"].months_to_value,
        )


# ============================================================
# RESULT GROUPS
# ============================================================

candidates = screen_data["candidates"]

survivors = [
    s for s in candidates
    if s["status"] == CandidateStatus.SURVIVOR
]

near_misses = [
    s for s in candidates
    if s["status"] == CandidateStatus.NEAR_MISS
]

failed_candidates = [
    s for s in candidates
    if s["status"] == CandidateStatus.FAIL
]

data_insufficient = [
    s for s in candidates
    if s["status"] == CandidateStatus.DATA_INSUFFICIENT
]


# ============================================================
# MOBILE STYLING
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

def display_gate_result(gate_number, result):

    if result is None:
        st.write(
            f"➖ **Gate {gate_number}: NOT EVALUATED**"
        )
        st.caption(
            "Stopped because an earlier gate did not pass."
        )
        return

    st.write(
        f"{gate_icon(result.status)} "
        f"**Gate {gate_number}: "
        f"{result.status.value}**"
    )

    st.caption(result.reason)


def display_stock(stock):

    with st.container(border=True):

        st.subheader(stock["ticker"])
        st.caption(stock["company"])

        if stock["status"] == CandidateStatus.SURVIVOR:

            st.success("SURVIVOR — Passed all 5 gates")

        elif stock["status"] == CandidateStatus.NEAR_MISS:

            st.error(
                f"Gate {stock['failed_gate']} FAIL — Near Miss"
            )

        elif stock["status"] == CandidateStatus.FAIL:

            st.error(
                f"Gate {stock['failed_gate']} FAIL"
            )

        elif (
            stock["status"]
            == CandidateStatus.DATA_INSUFFICIENT
        ):

            st.warning("DATA INSUFFICIENT")

        else:

            st.warning("NOT FULLY EVALUATED")

        col1, col2 = st.columns(2)

        col1.metric(
            "Current Price",
            format_money(stock["price"]),
        )

        col2.metric(
            "Fair Value",
            format_money(stock["fair_value"]),
        )

        col1.metric(
            "Downside Value",
            format_money(stock["downside_value"]),
        )

        col2.metric(
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
                display_gate_result(
                    gate_number,
                    stock["gate_results"].get(
                        gate_number
                    ),
                )

            if stock["gate_results"][5]:

                g5 = stock["gate_results"][5]
                metrics = g5.metrics

                st.markdown("### Gate 5 Valuation")

                st.write(
                    "**Base operating assumption:** "
                    + stock["gate5"].base_operating_assumption
                )

                st.write(
                    "**Fair-value range:** "
                    f"{format_money(stock['gate5'].fair_value_low)} "
                    "to "
                    f"{format_money(stock['gate5'].fair_value_high)}"
                )

                st.write(
                    "**Conservative fair value:** "
                    f"{format_money(stock['gate5'].conservative_fair_value)}"
                )

                st.write(
                    "**Adverse operating assumption:** "
                    + stock["gate5"].adverse_operating_assumption
                )

                st.write(
                    "**Downside range:** "
                    f"{format_money(stock['gate5'].downside_low)} "
                    "to "
                    f"{format_money(stock['gate5'].downside_high)}"
                )

                st.write(
                    "**Conservative downside:** "
                    f"{format_money(stock['gate5'].conservative_downside)}"
                )

                st.write(
                    "**Upside:** "
                    f"{format_percent(metrics.get('upside_percent'))}"
                )

                st.write(
                    "**Downside:** "
                    f"{format_percent(metrics.get('downside_percent'))}"
                )

                st.write(
                    "**Reward / downside:** "
                    f"{format_ratio(metrics.get('reward_downside'))}"
                )

                st.write(
                    "**Annualized base return:** "
                    f"{format_percent(metrics.get('annualized_return'))}"
                )

                if stock["recheck"]:

                    st.markdown("### Near-Miss Recheck")

                    st.write(
                        "Approximate maximum share price "
                        "that would satisfy both existing "
                        "Gate 5 hurdles:"
                    )

                    st.metric(
                        "Recheck Price",
                        format_money(
                            stock["recheck"]["qualifying_price"]
                        ),
                    )

                    st.caption(
                        "This does not change fair-value or downside "
                        "assumptions."
                    )


# ============================================================
# HEADER
# ============================================================

st.title("Contrarian Value Screen")

st.caption(
    "v6.3.1 — 6–18 month value + catalyst screen"
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
# DEVELOPMENT WARNING
# ============================================================

st.warning(
    "Development version: the gate engine is now based on "
    "v6.3.1, but the candidate evidence and valuation inputs "
    "below are still sample data."
)


# ============================================================
# RUN BUTTON
# ============================================================

if st.button(
    "Run New Screen",
    use_container_width=True,
):

    st.info(
        "The live candidate-discovery and data-retrieval "
        "workflow will be connected next."
    )


# ============================================================
# INITIAL CANDIDATE LIST
# ============================================================

st.divider()
st.header("Initial Candidate List")

for stock in candidates:

    st.write(
        f"**{stock['ticker']} — {stock['company']}**"
    )

    st.caption(
        "Development candidate used to test the "
        "screening workflow."
    )


# ============================================================
# DATA INSUFFICIENT
# ============================================================

st.divider()
st.header("Data-Insufficient Candidates")

if not data_insufficient:

    st.write("None.")

else:

    for stock in data_insufficient:
        display_stock(stock)


# ============================================================
# ELIMINATIONS
# ============================================================

st.divider()
st.header("Eliminations")

if not failed_candidates:

    st.write("No Gate 1–4 eliminations.")

else:

    for stock in failed_candidates:
        display_stock(stock)


# ============================================================
# SURVIVORS
# ============================================================

st.divider()
st.header("Survivors")

if not survivors:

    st.info("No candidates passed all five gates.")

else:

    for stock in survivors:
        display_stock(stock)


# ============================================================
# NEAR MISSES
# ============================================================

st.divider()
st.header("Near-Miss Recheck List")

if not near_misses:

    st.write("None.")

else:

    for stock in near_misses:
        display_stock(stock)


# ============================================================
# RANKING
# ============================================================

st.divider()
st.header("Survivor Ranking")

if not survivors:

    st.write("There is no survivor ranking.")

else:

    st.write(
        "Survivor ranking logic will be added after "
        "live evidence retrieval is connected."
    )


# ============================================================
# FINAL DISCIPLINE CHECK
# ============================================================

st.divider()
st.header("Discipline Check")

if not survivors:

    st.write("There is no #1 survivor.")

else:

    st.write(
        "Final recommendation discipline check will be "
        "performed after live-data screening is connected."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    f"Screen date: {screen_data['run_date']}"
)

st.caption(
    "Development build — sample candidate evidence only."
)
