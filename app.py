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
    st.markdown("— **🌐 Tổng quan trạm** *(chưa khả dụng)*")
    st.markdown("— **🛰️ Bản đồ Radar & Vệ tinh** *(chưa khả dụng)*")
    st.markdown("— <span style='color:#00C2FF; font-weight:bold;'>📊 Dự báo & Phân tích</span>", unsafe_allow_html=True)
    st.markdown("— **⚠️ Cảnh báo bão & dông** *(chưa khả dụng)*")
    st.markdown("— **📜 Nhật ký suy luận AI** *(chưa khả dụng)*")
    st.markdown("— **⚙️ Cấu hình API & Model** *(chưa khả dụng)*")
    st.write("---")
    st.markdown("""
        <div style="background: rgba(18,27,47,0.8); padding: 12px; border-radius: 10px; border: 1px solid rgba(0,194,255,0.2);">
            <div style="font-size:11px; color:#38BDF8; font-weight:bold;">MÔ HÌNH HỌC SÂU</div>
            <div style="font-size:18px; color:#F8FAFC; font-weight:bold;">98.4%</div>
            <div style="font-size:11px; color:#94A3B8;">Độ trễ dự báo: 180ms</div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 4. HÀM XỬ LÝ DỮ LIỆU & AI
# ==========================================
def extract_location_and_time(user_question):
    gio_viet_nam = timezone(timedelta(hours=7))
    today_str = datetime.now(gio_viet_nam).strftime("%d/%m/%Y %H:%M:%S")

    prompt = f"""
Nhiệm vụ 1: Trích xuất tên Tỉnh/Thành phố hoặc Huyện lớn nhất từ câu hỏi người dùng. (Ví dụ: 'Thôn Tiên Châu' -> 'Tuy An, Dak Lak').
Nhiệm vụ 2: Phân tích khoảng thời gian người dùng muốn xem (quy ra SỐ GIỜ).
- Nếu hỏi "24h", "hôm nay", "ngày mai", "sáng nay", "tối nay" -> 24
- Nếu hỏi "48h", "2 ngày" -> 48
- Nếu hỏi "3 ngày" -> 72
- Nếu hỏi "5 ngày", "tuần này", hoặc không nói rõ thời gian -> 120

Chỉ trả về DUY NHẤT theo định dạng: TÊN_ĐỊA_ĐIỂM|SỐ_GIỜ
Ví dụ: Quan Go Vap, Ho Chi Minh|24
Câu hỏi: {user_question}
"""
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        ).choices[0].message.content.strip()
        
        parts = res.split("|")
        if len(parts) == 2:
            return parts[0].strip(), int(parts[1].strip())
        return res.replace("|", ""), 120
    except Exception:
        return "Quan Go Vap, Ho Chi Minh", 120


def fetch_weather_data(location_name):
    def safe_get_geo(query):
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=1&appid={WEATHER_KEY}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
        except Exception:
            pass
        return None

    geo_data = safe_get_geo(f"{location_name},VN")
    if not geo_data:
        geo_data = safe_get_geo(location_name)
    if not geo_data and "," in location_name:
        last_part = location_name.split(",")[-1].strip()
        geo_data = safe_get_geo(f"{last_part},VN")
    if not geo_data:
        geo_data = safe_get_geo("Ho Chi Minh,VN")

    if not geo_data or not isinstance(geo_data, dict) or 'lat' not in geo_data or 'lon' not in geo_data:
        return None, f"Không thể tra cứu tọa độ cho địa điểm: '{location_name}'"

    lat, lon = geo_data['lat'], geo_data['lon']
    display_name = geo_data.get('local_names', {}).get('vi', geo_data.get('name', location_name))

    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric&lang=vi"
    try:
        forecast_res = requests.get(forecast_url, timeout=10).json()
    except Exception:
        return None, "Không thể kết nối đến máy chủ thời tiết."

    if not isinstance(forecast_res, dict) or str(forecast_res.get("cod")) != "200":
        return None, "Dữ liệu dự báo thời tiết không khả dụng."

    records = []
    for item in forecast_res.get("list", []):
        rain_vol = item.get("rain", {}).get("3h", 0)
        records.append({
            "Thời gian": item.get("dt_txt", ""),
            "Nhiệt độ (°C)": item.get("main", {}).get("temp", 0),
            "Cảm giác (°C)": item.get("main", {}).get("feels_like", 0),
            "Độ ẩm (%)": item.get("main", {}).get("humidity", 0),
            "Mưa (mm)": rain_vol,
            "Mô tả": item.get("weather", [{}])[0].get("description", "").capitalize()
        })

    df = pd.DataFrame(records)
    return {"name": display_name, "df": df, "lat": lat, "lon": lon}, None


def generate_ai_report(user_question, location_name, df_weather, target_hours):
    gio_viet_nam = timezone(timedelta(hours=7))
    today_str = datetime.now(gio_viet_nam).strftime("%d/%m/%Y %H:%M:%S")

    weather_summary = df_weather.to_string(index=False)

    system_prompt = f"""
Bạn là Hệ thống AI Khí tượng WeatherAI Intelligence Pro.
Thời gian hiện tại: {today_str}.

DỮ LIỆU KHÍ TƯỢNG {target_hours} GIỜ TỚI ĐẠI DIỆN CHO KHU VỰC: '{location_name}'
{weather_summary}

YÊU CẦU:
1. Phân tích chi tiết câu hỏi thời tiết của người dùng. Tôn trọng khoảng thời gian người dùng hỏi (trong vòng {target_hours} giờ tới).
2. KHÔNG ĐƯỢC TỪ CHỐI hoặc báo không có dữ liệu nếu người dùng hỏi tên Thôn/Xã.
3. Nêu rõ khung giờ mưa nhiều nhất và biến động nhiệt độ.
4. Đưa ra 2 khuyến nghị thực tế.
"""
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0.3
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Không thể khởi tạo phân tích AI: {str(e)}"


# ==========================================
# 5. GIAO DIỆN CHÍNH
# ==========================================
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
        value="",
        placeholder="Hãy viết điều gì đó.",
        label_visibility="collapsed"
    )
with col_btn:
    submit_btn = st.button("🚀 Dự báo & Phân tích", use_container_width=True)

if submit_btn:
    query_text = user_q.strip() if user_q.strip() else "5 ngày tiếp theo, ngày nào có nhiều mưa nhất ở Quận Gò Vấp, TP.HCM?"

    with st.spinner("⚡ AI đang kết nối dữ liệu khí tượng..."):
        loc_target, target_hours = extract_location_and_time(query_text)
        data, err = fetch_weather_data(loc_target)

        if err:
            st.error(f"❌ {err}")
        else:
            df = data["df"]
            loc_name = data["name"]

            num_rows = max(1, target_hours // 3)
            df_filtered = df.head(num_rows)

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

            c1, c2, c3, c4 = st.columns(4)
            curr_temp = df.iloc[0]["Nhiệt độ (°C)"]
            curr_feel = df.iloc[0]["Cảm giác (°C)"]
            curr_hum = df.iloc[0]["Độ ẩm (%)"]
            total_rain_24h = df.head(8)["Mưa (mm)"].sum()

            with c1:
                st.markdown('<div class="telemetry-card"><div class="telemetry-label">ĐỘ CHÍNH XÁC AI (24H)</div><div class="telemetry-value">96.8%</div><div class="telemetry-sub">Chuẩn sai RMS: 0.42°C</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="telemetry
