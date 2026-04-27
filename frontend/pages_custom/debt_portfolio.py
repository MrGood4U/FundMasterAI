import streamlit as st
from textwrap import dedent
from components.topbar import render_topbar


def html(content):
    st.markdown(dedent(content).strip(), unsafe_allow_html=True)


def render_debt_portfolio():
    render_topbar()

    html("""
<div class="metric-grid">
    <div class="metric-card">
        <div class="metric-label">TOTAL BOND VALUE</div>
        <div class="metric-value">--</div>
        <div class="muted">Data from backend API</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">AVERAGE YIELD</div>
        <div class="metric-value">--</div>
        <div class="muted">Data from backend API</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">DURATION</div>
        <div class="metric-value">--</div>
        <div class="muted">Data from backend API</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">CREDIT RATING</div>
        <div class="metric-value">--</div>
        <div class="muted">Data from backend API</div>
    </div>
</div>
""")

    html("""
<div class="two-col">
    <div class="card">
        <div class="section-title">Yield Comparison</div>
        <div class="placeholder-box">Yield chart API placeholder</div>
    </div>
    <div class="card">
        <div class="section-title">Risk Composition</div>
        <div class="placeholder-box">Risk composition API placeholder</div>
    </div>
</div>
""")

    html("""
<div class="card">
    <div class="section-title">Bond Holdings</div>
    <div class="placeholder-box">Bond holdings table will be loaded from backend.</div>
</div>
""")

    html("""
<div class="card">
    <div class="section-title">Maturity Ladder</div>
    <div class="placeholder-box">Maturity ladder data placeholder</div>
</div>
""")