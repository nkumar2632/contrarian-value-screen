import streamlit as st

from candidate_discovery import discover_candidates
from data_sources import get_yahoo_price


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
# CACHE
# ============================================================

@st.cache_data(ttl=1800)
def get_discovery_result_v2():
    """
    Discover, eligibility-screen, audit, and freeze candidates.

    Cached for 30 minutes so routine Streamlit reruns
    do not silently change the frozen list.

    v2 is intentionally used to invalidate older cached
    candidate objects after the discovery schema changed.
    """

    return discover_candidates(
        target_count=12
    )


@st.cache_data(ttl=300)
def retrieve_price(ticker):
    return get_yahoo_price(
        ticker
    )


# ============================================================
# FORMATTING
# ============================================================

def format_money(value):
    if value is None:
        return "N/A"

    return f"${value:,.2f}"


def format_market_cap(value):
    if value is None:
        return "N/A"

    if value >= 1_000_000_000:
        return (
            f"${value / 1_000_000_000:.1f}B"
        )

    if value >= 1_000_000:
        return (
            f"${value / 1_000_000:.1f}M"
        )

    return f"${value:,.0f}"


def format_large_money(value):
    if value is None:
        return "N/A"

    absolute_value = abs(
        value
    )

    if absolute_value >= 1_000_000_000:
        return (
            f"${value / 1_000_000_000:.2f}B"
        )

    if absolute_value >= 1_000_000:
        return (
            f"${value / 1_000_000:.2f}M"
        )

    return f"${value:,.0f}"


def format_percent(value):
    if value is None:
        return "N/A"

    return f"{value:.1%}"


def format_datetime(value):
    if value is None:
        return "N/A"

    return value.strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


def format_profitability(value):
    if value is True:
        return "Positive"

    if value is False:
        return "Negative"

    return "Unavailable / N/A"


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
# HEADER
# ============================================================

st.title(
    "Contrarian Value Screen"
)

st.caption(
    "v6.3.1 — live discovery + eligibility audit"
)

st.warning(
    "DISCOVERY STAGE ONLY: candidates below were generated "
    "from current market-dislocation signals and passed the "
    "basic discovery-universe eligibility screen. No candidate "
    "has passed an investment gate yet."
)


# ============================================================
# DISCOVER / AUDIT / FREEZE
# ============================================================

with st.spinner(
    "Scanning market dislocations and checking eligibility..."
):

    (
        candidates,
        eligibility_audit,
    ) = get_discovery_result_v2()


# ============================================================
# SUMMARY
# ============================================================

col1, col2, col3 = st.columns(3)

col1.metric(
    "Frozen",
    len(candidates),
)

col2.metric(
    "Eligibility Checked",
    len(eligibility_audit),
)

col3.metric(
    "Gated",
    0,
)


# ============================================================
# NEW SCREEN BUTTON
# ============================================================

if st.button(
    "Run New Discovery Screen",
    use_container_width=True,
):

    get_discovery_result_v2.clear()
    retrieve_price.clear()

    st.rerun()


# ============================================================
# UNIVERSE NOTE
# ============================================================

st.info(
    "Current discovery universe: S&P 500 constituents plus "
    "major unleveraged U.S.-listed ETFs. Stock candidates "
    "must satisfy the approximately $10B market-cap and "
    "profitability eligibility requirements before the final "
    "candidate list is frozen. This is not represented as a "
    "full U.S.-market screen."
)


# ============================================================
# ELIGIBILITY AUDIT
# ============================================================

st.divider()

st.header(
    "Eligibility Audit"
)

st.caption(
    "Candidates are shown in original dislocation-score order. "
    "Every security in the ranked discovery pool is audited, "
    "including names examined after the 12-name frozen list "
    "has already been filled."
)


accepted_count = sum(
    1
    for item in eligibility_audit
    if item.eligible
)

not_included_count = (
    len(eligibility_audit)
    - len(candidates)
)


audit_col1, audit_col2, audit_col3 = (
    st.columns(3)
)

audit_col1.metric(
    "Examined",
    len(eligibility_audit),
)

audit_col2.metric(
    "Eligible",
    accepted_count,
)

audit_col3.metric(
    "Not Frozen",
    not_included_count,
)


with st.expander(
    "Show full eligibility audit",
    expanded=False,
):

    for item in eligibility_audit:

        st.markdown(
            f"### #{item.discovery_rank} — {item.ticker}"
        )

        st.caption(
            item.company
        )

        if item.eligible:

            if any(
                candidate.ticker == item.ticker
                for candidate in candidates
            ):

                st.success(
                    "ELIGIBLE — included in frozen list"
                )

            else:

                st.info(
                    "ELIGIBLE — not frozen because the "
                    "12-name list was already full"
                )

        elif (
            item.eligibility_status
            == "DATA INSUFFICIENT"
        ):

            st.warning(
                "DATA INSUFFICIENT — not included"
            )

        else:

            st.error(
                "INELIGIBLE — not included"
            )

        audit_metric_1, audit_metric_2 = (
            st.columns(2)
        )

        audit_metric_1.metric(
            "Market Cap",
            format_market_cap(
                item.market_cap
            ),
        )

        audit_metric_2.metric(
            "Profitability",
            format_profitability(
                item.profitable
            ),
        )

        st.write(
            "**Reason:** "
            f"{item.eligibility_reason}"
        )

        st.write(
            "**Security type:** "
            f"{item.security_type}"
        )

        if item.net_income is not None:

            st.write(
                "**Retrieved annual net income:** "
                f"{format_large_money(item.net_income)}"
            )

        st.write(
            "**Eligibility source:** "
            f"{item.eligibility_source}"
        )

        st.write(
            "**Eligibility retrieved:** "
            f"{format_datetime(item.eligibility_retrieved_at)}"
        )

        st.write(
            "**Discovery score:** "
            f"{item.discovery_score:.2f}"
        )

        st.caption(
            item.entry_reason
        )

        st.divider()


# ============================================================
# INITIAL CANDIDATE LIST
# ============================================================

st.divider()

st.header(
    "A. Initial Candidate List"
)

if not candidates:

    st.error(
        "No eligible candidates were discovered from the "
        "current market-dislocation rules."
    )

else:

    st.caption(
        "The following list is frozen before investment "
        "gating. No replacement candidates will be added "
        "after Gate 1 begins."
    )

    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):

        with st.container(
            border=True
        ):

            st.subheader(
                f"{rank}. {candidate.ticker}"
            )

            st.caption(
                candidate.company
            )

            st.write(
                candidate.entry_reason
            )

            # --------------------------------------------
            # LIVE PRICE
            # --------------------------------------------

            price_result = retrieve_price(
                candidate.ticker
            )

            if price_result.error:

                st.warning(
                    "Current price retrieval unavailable."
                )

                st.caption(
                    price_result.error
                )

            else:

                st.metric(
                    "Current Retrieved Price",
                    format_money(
                        price_result.price
                    ),
                )

                st.caption(
                    f"Price source: {price_result.source}"
                )

                st.caption(
                    "Market timestamp: "
                    f"{format_datetime(price_result.market_time)}"
                )

            # --------------------------------------------
            # DISCOVERY METRICS
            # --------------------------------------------

            col1, col2 = st.columns(2)

            col1.metric(
                "1 Month",
                format_percent(
                    candidate.return_1m
                ),
            )

            col2.metric(
                "3 Months",
                format_percent(
                    candidate.return_3m
                ),
            )

            col1.metric(
                "6 Months",
                format_percent(
                    candidate.return_6m
                ),
            )

            col2.metric(
                "From 52W High",
                format_percent(
                    candidate.drawdown_from_52w_high
                ),
            )

            # --------------------------------------------
            # ELIGIBILITY
            # --------------------------------------------

            st.success(
                "✓ ELIGIBLE FOR FROZEN CANDIDATE LIST"
            )

            eligibility_col1, eligibility_col2 = (
                st.columns(2)
            )

            eligibility_col1.metric(
                "Market Cap",
                format_market_cap(
                    candidate.market_cap
                ),
            )

            eligibility_col2.metric(
                "Profitability",
                format_profitability(
                    candidate.profitable
                ),
            )

            st.caption(
                candidate.eligibility_reason
            )

            # --------------------------------------------
            # DETAILS
            # --------------------------------------------

            with st.expander(
                f"Why {candidate.ticker} entered"
            ):

                st.markdown(
                    "### Discovery Signals"
                )

                if candidate.signals:

                    for signal in candidate.signals:

                        st.write(
                            f"• {signal}"
                        )

                else:

                    st.write(
                        "No individual threshold signal recorded."
                    )

                st.markdown(
                    "### Eligibility"
                )

                st.write(
                    "**Status:** "
                    f"{candidate.eligibility_status}"
                )

                st.write(
                    "**Market capitalization:** "
                    f"{format_market_cap(candidate.market_cap)}"
                )

                st.write(
                    "**Profitability:** "
                    f"{format_profitability(candidate.profitable)}"
                )

                st.write(
                    "**Eligibility rationale:** "
                    f"{candidate.eligibility_reason}"
                )

                st.caption(
                    "Eligibility determines whether a security "
                    "may enter the frozen candidate list. It "
                    "does not establish undervaluation."
                )

                st.markdown(
                    "### Discovery Metadata"
                )

                st.write(
                    "**Discovery score:** "
                    f"{candidate.discovery_score:.2f}"
                )

                st.write(
                    "**Discovery source:** "
                    f"{candidate.discovery_source}"
                )

                st.write(
                    "**Discovery retrieved:** "
                    f"{format_datetime(candidate.retrieved_at)}"
                )

                st.caption(
                    "Discovery score ranks market dislocation "
                    "only. It is not a valuation score and "
                    "cannot pass Gate 1."
                )


# ============================================================
# DATA INSUFFICIENT
# ============================================================

st.divider()

st.header(
    "B. Data-Insufficient Candidates"
)

st.write(
    "Eligibility data insufficiency is shown in the audit "
    "above. Formal investment-gate data insufficiency will "
    "begin with Gate 1."
)


# ============================================================
# ELIMINATION TABLE
# ============================================================

st.divider()

st.header(
    "C. Elimination Table"
)

st.write(
    "No candidates have been evaluated by an investment "
    "gate yet."
)


# ============================================================
# SURVIVORS
# ============================================================

st.divider()

st.header(
    "D. Survivors"
)

st.info(
    "No survivor determination has been made."
)


# ============================================================
# NEAR MISSES
# ============================================================

st.divider()

st.header(
    "E. Near-Miss Recheck List"
)

st.write(
    "Not available until candidates reach Gate 4 or Gate 5."
)


# ============================================================
# RANKING
# ============================================================

st.divider()

st.header(
    "F. Ranking"
)

st.write(
    "There is no survivor ranking."
)


# ============================================================
# DISCIPLINE CHECK
# ============================================================

st.divider()

st.header(
    "Discipline Check"
)

st.write(
    "There is no #1 survivor."
)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Development build — live discovery and audited "
    "eligibility layers active; investment gates not yet "
    "connected."
)
