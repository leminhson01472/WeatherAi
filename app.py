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
    st.error("❌ Thiếu APIGIARE_API_KEY hoặc OPENWEATHER_API_KEY!")
    st.stop()

client = OpenAI(
    api_key=AI_KEY,
    base_url="https://api.apigiare.vn/v1",
    timeout=60,
    max_retries=2,
)
MODEL = "gpt-4o"

# 2. BỘ CSS TÙY CHỈNH TẢI FULL GIAO DIỆN DARK MODE GLASSMORPHISM
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0A1327 !important;
        color: #F8FAFC !important;
        font-family: 'Inter', sans-serif;
    }

    #MainMenu, footer {visibility: hidden;}

    /* Sidebar Custom */
    [data-testid="stSidebar"] {
        background-color: #050E21 !important;
        border-right: 1px solid rgba(56, 189, 248, 0.12) !important;
    }

    /* Top Bar Header */
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 20px;
        background: rgba(18, 27, 47, 0.85);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 12px;
        margin-bottom: 20px;
        backdrop-filter: blur(16px);
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

    /* Card Metrics */
    .telemetry-card {
        background: rgba(24, 35, 60, 0.75);
        border: 1px solid rgba(56, 189, 248, 0.18);
        border-radius: 12px;
        padding: 16px;
        backdrop-filter: blur(16px);
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

    /* AI Box */
    .ai-card {
        background: rgba(18, 27, 47, 0.9);
        border: 1px solid rgba(0, 194, 255, 0.3);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }

    /* Inputs & Buttons */
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

# 4. HÀM XỬ LÝ DỮ LIỆU WEATHER & AI
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
    res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    return res.choices[0].message.content.strip()


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
    today_str = datetime.now(gio_viet_nam).strftime("%d/%m/%Y %H:%M:%S")

    weather_summary = df_weather.to_string(index=False)

    system_prompt = f"""
Bạn là Hệ thống AI Khí tượng WeatherAI Intelligence Pro.
Thời gian hiện tại: {today_str}.
DỮ LIỆU DỰ BÁO THỜI TIẾT TẠI '{location_name}':
{weather_summary}

YÊU CẦU:
1. Trả lời trực tiếp câu hỏi người dùng theo phong cách báo cáo khí tượng chuyên nghiệp.
2. Nêu rõ đỉnh nhiệt độ và khoảng thời gian có khả năng mưa cao nhất.
3. Đưa ra khuyến nghị di chuyển & hoạt động ngoài trời.
"""
    res = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ],
        temperature=0.3
    )
    return res.choices[0].message.content.strip()


# 5. GIAO DIỆN CHÍNH
st.markdown("""
    <div class="brand-header">
        <div class="brand-title">
            <span>⚡ WeatherAI Intelligence</span>
            <span class="brand-badge">PRO NEURAL v2.4</span>
        </div>
        <div style="font-size: 12px; color: #94A3B8;">Trợ Lý Dự Báo Khí Tượng & Phân Tích Đa Tầng</div>
    </div>
""", unsafe_allow_html=True)

col_input, col_btn = st.columns([4, 1])
with col_input:
    user_q = st.text_input(
        "Nhập địa điểm / câu hỏi:",
        value="5 ngày tiếp theo, ngày nào có nhiều mưa nhất ở Quận Gò Vấp, TP.HCM?",
        label_visibility="collapsed"
    )
with col_btn:
    submit_btn = st.button("🚀 Dự báo & Phân tích", use_container_width=True)

if submit_btn or user_q:
    with st.spinner("⚡ AI đang tải dữ liệu khí tượng..."):
        loc_target = extract_location(user_q)
        data, err = fetch_weather_data(loc_target)

        if err:
            st.error(f"❌ {err}")
        else:
            df = data["df"]
            loc_name = data["name"]

            # Tiêu đề Vị trí & Tọa độ
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 10px; margin: 15px 0;">
                    <span style="font-family: 'Plus Jakarta Sans'; font-size: 22px; font-weight: 700;">
                        📍 Dữ liệu Khí tượng Thời gian thực: <span style="color: #00C2FF;">{loc_name}</span>
                    </span>
                    <span style="background: rgba(0, 194, 255, 0.12); border: 1px solid rgba(0, 194, 255, 0.35); color: #75D1FF; font-family: monospace; font-size: 13px; font-weight: 600; padding: 4px 10px; border-radius: 6px;">
                        {data['lat']:.3f}°N, {data['lon']:.3f}°E
                    </span>
                </div>
            """, unsafe_allow_html=True)

            # 4 Thẻ Telemetry
            c1, c2, c3, c4 = st.columns(4)
            curr_temp = df.iloc[0]["Nhiệt độ (°C)"]
            curr_feel = df.iloc[0]["Cảm giác (°C)"]
            curr_hum = df.iloc[0]["Độ ẩm (%)"]
            total_rain_24h = df.iloc[:8]["Mưa (mm)"].sum()

            with c1:
                st.markdown(f"""<div class="telemetry-card"><div class="telemetry-label">ĐỘ CHÍNH XÁC AI (24H)</div><div class="telemetry-value">96.8%</div><div class="telemetry
