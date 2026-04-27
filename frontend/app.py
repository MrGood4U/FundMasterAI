import streamlit as st

from components.styles import load_styles
from components.sidebar import render_sidebar

from pages_custom.overview import render_overview
from pages_custom.debt_portfolio import render_debt_portfolio
from pages_custom.fund_analysis import render_fund_analysis


st.set_page_config(
    page_title="FundMaster",
    page_icon="🏦",
    layout="wide"
)

load_styles()

page = render_sidebar()

if page == "overview":
    render_overview()

elif page == "debt":
    render_debt_portfolio()

elif page == "fund":
    render_fund_analysis()

else:
    st.error(f"Page not found: {page}")