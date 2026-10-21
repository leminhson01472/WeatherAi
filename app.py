import os
from datetime import datetime, timezone, timedelta
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# 1. CẤU HÌNH TRANG & API KEY
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

# 2. BỘ CSS GLASSMORPHISM DARK MODE
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

# 3. SIDEBAR NAVIGATION
with st.sidebar:
    st.markdown("### ⚡ KHÍ TƯỢNG VI MÔ")
    st.markdown("— **🌐 Tổng quan trạm**")
    st.markdown("— **🛰️ Bản đồ Radar & Vệ tinh**")
    st.markdown("— <span style='color:#00C2FF; font-weight:bold;'>📊 Dự báo & Phân tích 5 Ngày</span>", unsafe_allow_html=True)
    st.markdown("— **⚠️ Cảnh báo bão & dông**")
    st.markdown("— **📜 Nhật ký suy luận AI**")
    st.markdown("— **⚙️ Cấu hình API & Model**")
    st.write("---")
    st.markdown("""
        <div style="background: rgba(18,27,47,0.8); padding: 12px; border-radius: 10px; border: 1px solid rgba(0,194,255,0.2);">
            <div style="font-size:11px; color:#38BDF8; font-weight:bold;">MÔ HÌNH HỌC SÂU</div>
            <div style="font-size:18px; color:#F8FAFC; font-weight:bold;">98.4%</div>
            <div style="font-size:11px; color:#94A3B8;">Độ trễ dự báo: 180ms</div>
        </div>
    """, unsafe_allow_html=True)

# 4. HÀM XỬ LÝ DỮ LIỆU & AI
def extract_location(user_question):
    gio_viet_nam = timezone(timedelta(hours=7))
    today_str = datetime.now(gio_viet_nam).strftime("%d/%m/%Y %H:%M:%S")

    prompt = f"""
Trích xuất tên địa điểm từ câu hỏi để tra cứu thời tiết.
Nếu không có địa điểm cụ thể, trả về 'Quan Go Vap, Ho Chi Minh'.
Thời gian hiện tại: {today_str}.

Câu hỏi: {user_question}
Chỉ trả về DUY NHẤT tên địa điểm bằng tiếng Anh hoặc tiếng Việt không dấu.
"""
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        return res.choices[0].message.content.strip()
    except Exception:
        return "Quan Go Vap, Ho Chi Minh"


def fetch_weather_data(location_name):
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location_name},VN&limit=1&appid={WEATHER_KEY}"
    geo_res = requests.get(geo_url, timeout=10).json()

    if not geo_res:
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location_name}&limit=1&appid={WEATHER_KEY}"
        geo_res = requests.get(geo_url, timeout=10).json()

    if not geo_res:
        return None, f"Không tìm thấy vị trí: '{location_name}'"

    lat, lon = geo_res[0]['lat'], geo_res[0]['lon']
    display_name = geo_res[0].get('local_names', {}).get('vi', geo_res[0]['name'])

    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric&lang=vi"
    forecast_res = requests.get(forecast_url, timeout=10).json()

    if forecast_res.get("cod") != "200":
        return None, "Lỗi kết nối tới dịch vụ OpenWeatherMap."

    records = []
    for item in forecast_res["list"]:
        rain_vol = item.get("rain", {}).get("3h", 0)
        records.append({
            "Thời gian": item["dt_txt"],
            "Nhiệt độ (°C)": item["main"]["temp"],
            "Cảm giác (°C)": item["main"]["feels_like"],
            "Độ ẩm (%)": item["main"]["humidity"],
            "Mưa (mm)": rain_vol,
            "Mô tả": item["weather"][0]["description"].capitalize()
        })

    df = pd.DataFrame(records)
    return {"name": display_name, "df": df, "lat": lat, "lon": lon}, None


def generate_ai_report(user_question, location_name, df_weather):
    gio_viet_nam = timezone(timedelta(hours=7))
    today_str = datetime.now(gio_viet_
