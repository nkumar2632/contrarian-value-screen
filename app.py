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
def get_frozen_candidates():
    """
    Discover and freeze the candidate list.

    Cached for 30 minutes so routine Streamlit reruns
    do not silently change the frozen list.
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
    "v6.3.1 — live candidate discovery"
)

st.warning(
    "DISCOVERY STAGE ONLY: the candidate list below is "
    "generated from current market dislocation signals. "
    "No candidate has passed any investment gate yet."
)


# ============================================================
# DISCOVER / FREEZE
# ============================================================

with st.spinner(
    "Scanning current large-cap market dislocations..."
):

    candidates = get_frozen_candidates()


# ============================================================
# SUMMARY
# ============================================================

col1, col2, col3 = st.columns(3)

col1.metric(
    "Frozen Candidates",
    len(candidates),
)

col2.metric(
    "Target",
    12,
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

    get_frozen_candidates.clear()
    retrieve_price.clear()

    st.rerun()


# ============================================================
# UNIVERSE NOTE
# ============================================================

st.info(
    "Current discovery universe: S&P 500 constituents plus "
    "major unleveraged U.S.-listed ETFs. This is a reproducible "
    "large-cap universe and is not represented as a full "
    "U.S.-market screen."
)


# ============================================================
# INITIAL CANDIDATE LIST
# ============================================================

st.divider()

st.header(
    "A. Initial Candidate List"
)

if not candidates:

    st.error(
        "No candidates were discovered from the current "
        "market-dislocation rules."
    )

else:

    st.caption(
        "This list is frozen before gating. No replacement "
        "candidates will be added after failures."
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

            # ----------------------------------------
            # LIVE PRICE
            # ----------------------------------------

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

            # ----------------------------------------
            # DISCOVERY METRICS
            # ----------------------------------------

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
                    "Discovery score ranks market dislocation only. "
                    "It is not a valuation score and is not used to "
                    "pass Gate 1."
                )


# ============================================================
# DATA INSUFFICIENT
# ============================================================

st.divider()

st.header(
    "B. Data-Insufficient Candidates"
)

st.write(
    "Not evaluated yet. Data-retrieval protocol will begin "
    "with Gate 1 research."
)


# ============================================================
# ELIMINATION TABLE
# ============================================================

st.divider()

st.header(
    "C. Elimination Table"
)

st.write(
    "No candidates have been gated yet."
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
    "Development build — live discovery layer active; "
    "investment gates not yet connected."
)
