import streamlit as st
from textwrap import dedent
from components.topbar import render_topbar


def render_fund_analysis():
    render_topbar()

    st.markdown(dedent("""
    <div class="card">
        <div style="display:grid;grid-template-columns:2fr 1fr;align-items:center;">
            <div>
                <div class="asset-title">Fund Analysis</div>
                <div class="muted">Fund basic information will be loaded from backend API.</div>
            </div>
            <div>
                <div class="metric-label" style="text-align:right;">CURRENT PRICE</div>
                <div class="big-gain">--</div>
            </div>
        </div>
    </div>

    <div class="two-col">
        <div class="card">
            <div class="section-title">Performance Curve</div>
            <div class="placeholder-box">Performance chart API placeholder</div>
        </div>

        <div class="card">
            <div class="section-title">Risk Indicators</div>
            <div class="placeholder-box">Sharpe / Volatility / Alpha / Beta placeholder</div>
        </div>
    </div>

    <div class="card">
        <div class="section-title">Asset Allocation</div>
        <div class="placeholder-box">Asset allocation data will be loaded from backend.</div>
    </div>

    <div class="card">
        <div class="section-title">Management Team & Major Holdings</div>
        <div class="placeholder-box">Manager and holdings information placeholder</div>
    </div>

    <div class="card">
        <div class="section-title">AI Fund Analysis</div>
        <div class="placeholder-box">AI analysis result placeholder</div>
    </div>
    """), unsafe_allow_html=True)