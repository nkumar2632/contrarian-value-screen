import streamlit as st

st.set_page_config(
    page_title="Contrarian Value Screen",
    page_icon="📉",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# SAMPLE SCREEN DATA
# -----------------------------

screen_data = {
    "run_date": "2026-09-01",
    "candidates": [
        {
            "ticker": "CMCSA",
            "company": "Comcast",
            "status": "NEAR MISS",
            "failed_gate": 5,
            "price": 31.20,
            "fair_value": 39.00,
            "downside_value": 25.00,
            "reward_downside": 1.26,
            "catalyst": "Broadband stabilization and improving free cash flow",
            "bear_case": "Continued broadband subscriber losses and weak cable economics",
            "failure_reason": "Did not meet required Gate 5 reward/downside threshold",
            "gates": {
                1: "PASS",
                2: "PASS",
                3: "PASS",
                4: "PASS",
                5: "FAIL",
            },
        },
        {
            "ticker": "PYPL",
            "company": "PayPal",
            "status": "NEAR MISS",
            "failed_gate": 5,
            "price": 61.00,
            "fair_value": 75.00,
            "downside_value": 50.00,
            "reward_downside": 1.27,
            "catalyst": "Margin improvement and renewed branded checkout growth",
            "bear_case": "Competitive pressure and structurally slower transaction growth",
            "failure_reason": "Did not meet required Gate 5 reward/downside threshold",
            "gates": {
                1: "PASS",
                2: "PASS",
                3: "PASS",
                4: "PASS",
                5: "FAIL",
            },
        },
        {
            "ticker": "ADBE",
            "company": "Adobe",
            "status": "NEAR MISS",
            "failed_gate": 5,
            "price": 291.52,
            "fair_value": 337.00,
            "downside_value": 200.00,
            "reward_downside": 0.50,
            "catalyst": "AI monetization and stabilization of Creative Cloud growth",
            "bear_case": "Generative AI competition pressures pricing and growth",
            "failure_reason": "Insufficient upside relative to modeled downside",
            "gates": {
                1: "PASS",
                2: "PASS",
                3: "PASS",
                4: "PASS",
                5: "FAIL",
            },
        },
    ],
}

# -----------------------------
# DERIVED RESULTS
# -----------------------------

candidates = screen_data["candidates"]

survivors = [
    stock for stock in candidates
    if stock["status"] == "SURVIVOR"
]

near_misses = [
    stock for stock in candidates
    if stock["status"] == "NEAR MISS"
]

# -----------------------------
# MOBILE-FIRST CSS
# -----------------------------

st.markdown(
    """
    <style>
    .block-container {
        max-width: 720px;
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .ticker-card {
        border: 1px solid rgba(128,128,128,0.30);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 14px;
    }

    .ticker-card h3 {
        margin-bottom: 4px;
    }

    .ticker-card p {
        margin-top: 6px;
        margin-bottom: 6px;
    }

    div.stButton > button {
        width: 100%;
        min-height: 48px;
        font-size: 1rem;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# HEADER
# -----------------------------

st.title("Contrarian Value Screen")
st.caption("6–18 month value + catalyst opportunities")

col1, col2, col3 = st.columns(3)

col1.metric("Candidates", len(candidates))
col2.metric("Survivors", len(survivors))
col3.metric("Near Misses", len(near_misses))

if st.button("Run New Screen", use_container_width=True):
    st.info("Screening engine will be connected in a later step.")

st.divider()

# -----------------------------
# SURVIVORS
# -----------------------------

st.subheader("Survivors")

if len(survivors) == 0:
    st.write("No candidates passed all five gates.")

for stock in survivors:

    st.markdown(
        f"""
        <div class="ticker-card">
            <h3>{stock["ticker"]}</h3>
            <strong>PASS — All Gates</strong>
            <p><strong>Price:</strong> ${stock["price"]:.2f}</p>
            <p><strong>Fair value:</strong> ${stock["fair_value"]:.2f}</p>
            <p><strong>Downside:</strong> ${stock["downside_value"]:.2f}</p>
            <p><strong>Reward / Downside:</strong> {stock["reward_downside"]:.2f}×</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# NEAR MISSES
# -----------------------------

st.divider()
st.subheader("Near Misses")

for stock in near_misses:

    st.markdown(
        f"""
        <div class="ticker-card">
            <h3>{stock["ticker"]}</h3>
            <strong>Gate {stock["failed_gate"]} FAIL</strong>
            <p><strong>Price:</strong> ${stock["price"]:.2f}</p>
            <p><strong>Fair value:</strong> ${stock["fair_value"]:.2f}</p>
            <p><strong>Downside:</strong> ${stock["downside_value"]:.2f}</p>
            <p><strong>Reward / Downside:</strong> {stock["reward_downside"]:.2f}×</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(f"View full {stock['ticker']} analysis"):

        st.write(f"**Company:** {stock['company']}")

        st.write("**Gate results:**")
        for gate_number, result in stock["gates"].items():
            st.write(f"Gate {gate_number}: {result}")

        st.write("**Catalyst**")
        st.write(stock["catalyst"])

        st.write("**Bear case**")
        st.write(stock["bear_case"])

        st.write("**Why it failed**")
        st.write(stock["failure_reason"])

# -----------------------------
# RUN INFORMATION
# -----------------------------

st.divider()
st.caption(f"Screen date: {screen_data['run_date']}")
