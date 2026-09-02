import streamlit as st

st.set_page_config(
    page_title="Contrarian Value Screen",
    page_icon="📉",
    layout="centered",
    initial_sidebar_state="collapsed",
)

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

    .metric {
        font-size: 1.05rem;
        font-weight: 600;
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

st.title("Contrarian Value Screen")

st.caption("6–18 month value + catalyst opportunities")

col1, col2, col3 = st.columns(3)

col1.metric("Candidates", 12)
col2.metric("Survivors", 0)
col3.metric("Near Misses", 3)

st.button("Run New Screen", use_container_width=True)

st.divider()

st.subheader("Current Results")

with st.container():
   st.markdown(
    """
    <div class="ticker-card">
        <h3>ADBE</h3>
        <strong>Gate 5 FAIL</strong>
        <p><strong>Price:</strong> $291.52</p>
        <p><strong>Fair value:</strong> $337</p>
        <p><strong>Downside:</strong> $200</p>
        <p><strong>Reward / Downside:</strong> 0.50×</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("View full ADBE analysis"):
    st.write("Detailed valuation, catalyst, bear case, and invalidation will go here.")

st.divider()

st.subheader("Near Misses")

st.write("CMCSA")
st.write("PYPL")
st.write("ADBE")
