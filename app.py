import os
from datetime import datetime, timezone, timedelta
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ==========================================
# 1. CẤU HÌNH TRANG & KẾT NỐI API KEY
# ==========================================
load_dotenv()

AI_KEY = os.getenv("APIGIARE_API_KEY") or (st.secrets.get("APIGIARE_API_KEY") if "APIGIARE_API_KEY" in st.secrets else None)
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY") or (st.secrets.get("OPENWEATHER_API_KEY") if "OPENWEATHER_API_KEY" in st.secrets else None)

st.set_page_config(
    page_title="WeatherAI Intelligence PRO",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

if not AI_KEY or not WEATHER_KEY:
    st.error("❌ Thiếu APIGIARE_API_KEY hoặc OPENWEATHER_API_KEY trong cấu hình Secrets!")
    st.stop()

client = OpenAI(
    api_key=AI_KEY,
    base_url="https://api.apigiare.vn/v1",
    timeout=60,
    max_retries=2,
)
MODEL = "gpt-4o"

# ==========================================
# 2. BỘ CSS GLASSMORPHISM DARK MODE
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0A1327 !important;
        color: #F8FAFC !important;
        font-family: 'Inter', sans-serif;
    }

    #MainMenu, footer {visibility: hidden;}

    [data-testid="stSidebar"] {
        background-color: #050E21 !important;
        border-right: 1px solid rgba(56, 189, 248, 0.12) !important;
    }

    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 20px;
        background: rgba(18, 27, 47, 0.85);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .brand-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 20px;
        font-weight: 800;
        color: #F8FAFC;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .brand-badge {
        background: rgba(0, 194, 255, 0.15);
        border: 1px solid rgba(0, 194, 255, 0.4);
        color: #00C2FF;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 999px;
    }

    .telemetry-card {
        background: rgba(24, 35, 60, 0.75);
        border: 1px solid rgba(56, 189, 248, 0.18);
        border-radius: 12px;
        padding: 16px;
    }
    .telemetry-label {
        font-size: 11px;
        font-weight: 600;
        color: #94A3B8;
        text-transform: uppercase;
    }
    .telemetry-value {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 26px;
        font-weight: 700;
        color: #F8FAFC;
        margin: 6px 0;
    }
    .telemetry-sub {
        font-size: 12px;
        color: #38BDF8;
    }

    .ai-card {
        background: rgba(18, 27, 47, 0.9);
        border: 1px solid rgba(0, 194, 255, 0.35);
        border-left: 4px solid #00C2FF;
        border-radius: 12px;
        padding: 20px;
        margin-top: 15px;
        line-height: 1.6;
    }

    .stTextInput > div > div > input {
        background-color: rgba(18, 27, 47, 0.9) !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        color: #F8FAFC !important;
        border-radius: 8px !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #00C2FF 0%, #0284C7 100%) !important;
        color: #0A1327 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.markdown("### ⚡ KHÍ TƯỢNG VI MÔ")
    st.markdown("— **🌐 Tổng quan trạm** *(chưa khả dụng)*
