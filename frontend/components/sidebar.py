import streamlit as st


def render_sidebar():
    if "page" not in st.session_state:
        st.session_state.page = "overview"

    with st.sidebar:
        st.markdown("""
        <div class="logo-title">🏦 FundMaster</div>
        <div class="logo-subtitle">STRATEGIC CAPITAL</div>
        """, unsafe_allow_html=True)

        if st.button("▦ Overview", key="overview_btn"):
            st.session_state.page = "overview"
            st.rerun()

        if st.button("▣ Debt Portfolio", key="debt_btn"):
            st.session_state.page = "debt"
            st.rerun()

        if st.button("◎ Fund Analysis", key="fund_btn"):
            st.session_state.page = "fund"
            st.rerun()

        st.markdown("""
        <div class="nav-static">↗ Markets</div>
        <div class="nav-static">▤ News</div>
        <div class="nav-static">✺ AI Insights</div>
        <div class="nav-static">⚙ Settings</div>
        """, unsafe_allow_html=True)

    return st.session_state.page