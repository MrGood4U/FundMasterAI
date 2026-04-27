import streamlit as st


def render_topbar():
    st.markdown("""
    <div class="topbar">
        <div class="search-box">🔍 &nbsp; Search markets, assets, or indices...</div>
        <div class="user-box">
            🔔 &nbsp; ↻ &nbsp;&nbsp; Alexander Thorne<br>
            <span class="muted">Chief Strategist</span>
        </div>
    </div>
    """, unsafe_allow_html=True)