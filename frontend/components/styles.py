import streamlit as st


def load_styles():
    st.markdown("""
    <style>
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
    }

    .stApp {
        background-color: #07111d;
        color: #e5e7eb;
    }

    .block-container {
        padding-top: 3rem;
        padding-left: 3.5rem;
        padding-right: 3.5rem;
        max-width: 1300px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c1b2a, #081421);
        border-right: 1px solid #1f2a37;
        width: 290px !important;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 45px;
    }

    .logo-title {
        color: #19d3e6;
        font-size: 26px;
        font-weight: 900;
        margin-bottom: 6px;
    }

    .logo-subtitle {
        color: #9ca3af;
        font-size: 11px;
        letter-spacing: 3px;
        margin-bottom: 38px;
    }

    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        background: transparent !important;
        border: none !important;
        color: #8a96a8 !important;
        text-align: left !important;
        font-size: 16px !important;
        font-weight: 800 !important;
        padding: 16px 22px !important;
        margin: 6px 0 !important;
        border-radius: 4px !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover,
    section[data-testid="stSidebar"] .stButton > button:focus {
        background-color: #172231 !important;
        color: #19d3e6 !important;
        border-left: 4px solid #18d7e8 !important;
    }

    .nav-static {
        color: #8a96a8;
        padding: 15px 22px;
        margin: 8px 0;
        font-size: 15px;
        font-weight: 800;
    }

    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
    }

    .search-box {
        background-color: #030718;
        color: #8a96a8;
        border: 1px solid #101827;
        border-radius: 28px;
        padding: 14px 28px;
        width: 430px;
        font-size: 14px;
    }

    .user-box {
        text-align: right;
        color: #d1d5db;
        font-size: 14px;
    }

    .card {
        background-color: #111923;
        border: 1px solid #12333d;
        box-shadow: 0 0 14px rgba(0, 255, 255, 0.08);
        border-radius: 6px;
        padding: 28px 34px;
        margin-bottom: 24px;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 18px;
        margin-bottom: 24px;
    }

    .metric-card {
        background-color: #111923;
        border: 1px solid #12333d;
        border-radius: 6px;
        padding: 24px;
        box-shadow: 0 0 14px rgba(0, 255, 255, 0.06);
    }

    .metric-label {
        color: #9ca3af;
        font-size: 12px;
        letter-spacing: 2px;
        font-weight: 800;
    }

    .metric-value {
        color: #e5e7eb;
        font-size: 28px;
        font-weight: 900;
        margin-top: 12px;
    }

    .asset-title {
        font-size: 26px;
        font-weight: 900;
        color: #e5e7eb;
    }

    .section-title {
        font-size: 22px;
        font-weight: 900;
        color: #e5e7eb;
        margin-bottom: 12px;
    }

    .table-row {
        display: grid;
        grid-template-columns: 2.2fr 1.2fr 1.2fr 1.2fr;
        align-items: center;
        padding: 18px 0;
        border-bottom: 1px solid #1b2635;
    }

    .table-head {
        color: #9ca3af;
        font-size: 12px;
        letter-spacing: 2px;
        font-weight: 900;
    }

    .asset-name {
        color: #e5e7eb;
        font-size: 17px;
        font-weight: 800;
    }

    .two-col {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 22px;
        margin-bottom: 24px;
    }

    .placeholder-box {
        margin-top: 18px;
        padding: 45px;
        min-height: 120px;
        border: 1px dashed #24485a;
        border-radius: 6px;
        color: #8a96a8;
        background-color: #0c1520;
        text-align: center;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .green { color: #00e68a; font-weight: 900; }
    .red { color: #ff6b6b; font-weight: 900; }
    .cyan { color: #19d3e6; font-weight: 900; }
    .muted { color: #9ca3af; font-size: 13px; }

    .big-gain {
        color: #00e68a;
        font-size: 34px;
        font-weight: 900;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)