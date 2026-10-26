import os
import json
from datetime import datetime, timezone, timedelta
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from openai import OpenAI

# ==========================================
# 1. CẤU HÌNH TRANG & XÁC THỰC GOOGLE LOGIN
# ==========================================
load_dotenv()

AI_KEY = os.getenv("APIGIARE_API_KEY") or (st.secrets.get("APIGIARE_API_KEY") if "APIGIARE_API_KEY" in st.secrets else None)
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY") or (st.secrets.get("OPENWEATHER_API_KEY") if "OPENWEATHER_API_KEY" in st.secrets else None)

st.set_page_config(
    page_title="WeatherAI Pro - Trợ lý Khí tượng AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kiểm tra trạng thái Đăng nhập Google
if not st.user.is_logged_in:
    st.markdown("""
        <div style="text-align: center; padding: 60px 20px;">
            <div style="width: 70px; height: 70px; border-radius: 50%; background: #00C2FF; display: inline-flex; align-items: center; justify-content: center; color: #0A1327; box-shadow: 0 0 35px rgba(0,194,255,0.5); font-size: 36px; margin-bottom: 24px;">
                ⚡
            </div>
            <h1 style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 40px; font-weight: 800; color: #F8FAFC; margin-bottom: 12px;">WeatherAI Pro</h1>
            <p style="font-size: 16px; color: #94A3B8; max-width: 520px; margin: 0 auto 32px auto; line-height: 1.6;">
                Hệ thống phân tích khí tượng AI đa tầng, dự báo thời tiết theo thời gian thực và quản lý cuộc trò chuyện thông minh.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.info("🔒 Vui lòng đăng nhập bằng tài khoản Google để trải nghiệm và lưu trữ lịch sử các đoạn chat.")
        if st.button("🔑 Đăng nhập / Đăng ký bằng Google", use_container_width=True, type="primary"):
            st.login("google")
    st.stop()

# Đã đăng nhập thành công
user_email = st.user.email
user_name = st.user.name

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

# Key LocalStorage quản lý danh sách đoạn chat theo Email
USER_STORAGE_KEY = f"weatherai_pro_threads_{user_email.replace('@', '_at_').replace('.', '_')}"

# ==========================================
# 2. ĐỒNG BỘ LOCALSTORAGE CÁC PHIÊN TRÒ CHUYỆN (SESSIONS)
# ==========================================
# Cấu trúc threads_store: { "session_id_1": {"title": "Thời tiết TP.HCM", "created_at": "...", "chats": [...]}, ... }
if "threads_store" not in st.session_state:
    st.session_state.threads_store = {}

if "active_thread_id" not in st.session_state:
    st.session_state.active_thread_id = None

# Đọc dữ liệu các đoạn chat từ Web LocalStorage
local_storage_js = f"""
<script>
    const STORAGE_KEY = '{USER_STORAGE_KEY}';

    function syncFromWebStorage() {{
        const storedData = localStorage.getItem(STORAGE_KEY);
        if (storedData) {{
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: storedData
            }}, '*');
        }} else {{
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: '{{}}'
            }}, '*');
        }}
    }}
    setTimeout(syncFromWebStorage, 300);
</script>
"""

web_storage_data = components.html(local_storage_js, height=0)

if web_storage_data and isinstance(web_storage_data, str) and not st.session_state.threads_store:
    try:
        loaded_threads = json.loads(web_storage_data)
        if isinstance(loaded_threads, dict):
            st.session_state.threads_store = loaded_threads
            if loaded_threads and not st.session_state.active_thread_id:
                # Mặc định chọn phiên trò chuyện mới nhất
                st.session_state.active_thread_id = list(loaded_threads.keys())[-1]
    except Exception:
        pass

# Tạo một đoạn chat mới nếu chưa có phiên nào
def create_new_thread():
    new_id = f"chat_{int(datetime.now().timestamp() * 1000)}"
    st.session_state.threads_store[new_id] = {
        "title": "Cuộc trò chuyện mới",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chats": []
    }
    st.session_state.active_thread_id = new_id
    save_threads_to_web()

def save_threads_to_web():
    updated_json = json.dumps(st.session_state.threads_store, ensure_ascii=False)
    save_js = f"""
    <script>
        localStorage.setItem('{USER_STORAGE_KEY}', {json.dumps(updated_json)});
    </script>
    """
    components.html(save_js, height=0)

if not st.session_state.threads_store:
    create_new_thread()

if not st.session_state.active_thread_id or st.session_state.active_thread_id not in st.session_state.threads_store:
    st.session_state.active_thread_id = list(st.session_state.threads_store.keys())[-1]

# Lấy GPS an toàn
try:
    from streamlit_js_eval import get_geolocation
    user_gps = get_geolocation()
except Exception:
    user_gps = None

# ==========================================
# 3. SIDEBAR NAVIGATION (GIỐNG GEMINI)
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 15px;">
            <div style="width: 36px; height: 36px; border-radius: 50%; background: #00C2FF; display: flex; align-items: center; justify-content: center; color: #0A1327; box-shadow: 0 0 15px rgba(0,194,255,0.4); font-size: 18px;">
                ⚡
            </div>
            <div>
                <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 17px; font-weight: 800; color: #F8FAFC !important;">WeatherAI Pro</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Nút Tạo cuộc trò chuyện mới
    if st.button("➕ Cuộc trò chuyện mới", use_container_width=True, type="primary"):
        create_new_thread()
        st.rerun()

    st.write("---")
    
    # DANH SÁCH CÁC ĐOẠN CHAT (GIỐNG GEMINI SIDEBAR)
    st.markdown("<div style='font-size: 12px; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 8px;'>Tất cả cuộc trò chuyện</div>", unsafe_allow_html=True)
    
    # Duyệt danh sách các thread đảo ngược (mới nhất lên trên)
    sorted_thread_ids = list(st.session_state.threads_store.keys())[::-1]
    
    for tid in sorted_thread_ids:
        thread_info = st.session_state.threads_store[tid]
        title = thread_info.get("title", "Cuộc trò chuyện mới")
        is_selected = (tid == st.session_state.active_thread_id)
        
        # Rút ngắn tiêu đề nếu quá dài
        display_title = (title[:22] + '...') if len(title) > 22 else title
        
        btn_label = f"💬 {display_title}" if not is_selected else f"🔹 {display_title}"
        if st.button(btn_label, key=f"btn_thread_{tid}", use_container_width=True):
            st.session_state.active_thread_id = tid
            st.rerun()

    st.write("---")

    active_menu = st.radio(
        "📌 Chức năng chính:",
        [
            "📊 Dự báo & Trò chuyện",
            "🛰️ Bản đồ Radar & Vệ tinh",
            "⚠️ Cảnh báo dông bão"
        ],
        index=0
    )
    
    st.write("---")
    
    # Thông tin tài khoản & Nút xóa
    st.markdown(f"""
        <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); padding: 10px; border-radius: 10px; margin-bottom: 10px;">
            <div style="font-size: 12px; font-weight: 700; color: #F8FAFC !important;">👤 {user_name}</div>
            <div style="font-size: 10px; color: #94A3B8 !important; overflow: hidden; text-overflow: ellipsis;">{user_email}</div>
        </div>
    """, unsafe_allow_html=True)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("🗑️ Xóa đoạn chat này", use_container_width=True):
            if st.session_state.active_thread_id in st.session_state.threads_store:
                del st.session_state.threads_store[st.session_state.active_thread_id]
                save_threads_to_web()
                if st.session_state.threads_store:
                    st.session_state.active_thread_id = list(st.session_state.threads_store.keys())[-1]
                else:
                    create_new_thread()
                st.rerun()
    with col_s2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.logout()

# ==========================================
# 4. DYNAMIC CSS STYLES (DARK GLASS)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0A1327 !important;
        color: #F8FAFC !important;
        font-family: 'Inter', sans-serif;
    }

    #MainMenu, footer {visibility: hidden;}

    [data-testid="stSidebar"] {
        background-color: rgba(5, 14, 33, 0.9) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(56, 189, 248, 0.15) !important;
    }

    [data-testid="stSidebar"] *, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] div {
        color: #F8FAFC !important;
    }

    .stTextInput > div > div > input {
        background-color: rgba(18, 27, 47, 0.85) !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        color: #FFFFFF !important;
        border-radius: 9999px !important;
        padding: 12px 24px !important;
        font-size: 14px !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: #94A3B8 !important;
    }

    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #00C2FF 0%, #0284C7 100%) !important;
        color: #0A1327 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 9999px !important;
        padding: 8px 20px !important;
    }

    .hero-title {
        text-align: center;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: #F8FAFC;
        margin-bottom: 20px;
    }

    .telemetry-card {
        background: rgba(24, 35, 60, 0.75);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(56, 189, 248, 0.18);
        border-radius: 16px;
        padding: 16px;
    }
    .telemetry-label {
        font-size: 11px;
        font-weight: 700;
        color: #94A3B8 !important;
        text-transform: uppercase;
    }
    .telemetry-value {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 24px;
        font-weight: 700;
        color: #F8FAFC !important;
        margin: 4px 0;
    }
    .telemetry-sub {
        font-size: 12px;
        color: #38BDF8 !important;
    }

    .user-msg-card {
        background: rgba(56, 189, 248, 0.15);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 16px;
        padding: 14px 18px;
        margin-top: 15px;
        color: #F8FAFC !important;
    }

    .ai-card {
        background: rgba(18, 27, 47, 0.85);
        border: 1px solid rgba(0, 194, 255, 0.35);
        border-left: 4px solid #00C2FF;
        border-radius: 16px;
        padding: 18px;
        margin-top: 10px;
        margin-bottom: 20px;
        line-height: 1.6;
        color: #F8FAFC !important;
    }
    
    .alert-box {
        background: rgba(239, 68, 68, 0.2);
        border: 1px solid rgba(239, 68, 68, 0.4);
        border-left: 4px solid #EF4444;
        border-radius: 16px;
        padding: 18px;
        color: #F8FAFC !important;
    }
    .safe-box {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-left: 4px solid #10B981;
        border-radius: 16px;
        padding: 18px;
        color: #F8FAFC !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 5. HÀM XỬ LÝ DỮ LIỆU & AI
# ==========================================
def parse_user_intent(user_question):
    prompt = f"""
Phân tích câu hỏi người dùng và trả về định dạng JSON/Text ngắn gọn:
1. Ý định (is_weather): Trả về 'STORM' nếu hỏi về siêu bão, bão, áp thấp. Trả về 'WEATHER' nếu người dùng hỏi tra cứu thời tiết địa phương. Trả về 'CHAT' nếu chỉ chào hỏi, tán gẫu.
2. Tên địa điểm (location): Tên Tỉnh/Thành/Huyện/Bão. Trả về 'USE_GPS' nếu không nhắc tới địa danh.
3. Khoảng thời gian (hours): Số giờ cần xem (24, 48, 72, 120). Mặc định là 120.

Chỉ trả về 1 dòng duy nhất theo định dạng: LOẠI|TÊN_ĐỊA_ĐIỂM|SỐ_GIỜ
Câu hỏi: {user_question}
"""
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        ).choices[0].message.content.strip()
        
        parts = res.split("|")
        intent_type = parts[0].strip().upper() if len(parts) > 0 else "CHAT"
        loc = parts[1].strip() if len(parts) > 1 else "USE_GPS"
        hrs = int(parts[2].strip()) if (len(parts) > 2 and parts[2].strip().isdigit()) else 120
        return intent_type, loc, hrs
    except Exception:
        return "WEATHER", "USE_GPS", 120


def fetch_weather_by_coords(lat, lon):
    display_name = None
    try:
        geo_detail_url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=vi"
        res_geo = requests.get(geo_detail_url, timeout=5).json()
        locality = res_geo.get("locality", "")
        city = res_geo.get("city", "") or res_geo.get("principalSubdivision", "")
        if locality and city:
            display_name = f"{locality}, {city}"
        elif locality:
            display_name = locality
    except Exception:
        pass

    if not display_name:
        display_name = "Vị trí GPS của bạn"

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
    return {"name": display_name, "records": df.to_dict(orient="records"), "lat": lat, "lon": lon}, None


def fetch_weather_data(location_name):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={location_name}&limit=1&appid={WEATHER_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                lat, lon = data[0]['lat'], data[0]['lon']
                return fetch_weather_by_coords(lat, lon)
    except Exception:
        pass
    return fetch_weather_by_coords(10.8231, 106.6297)


def generate_general_chat(user_question):
    system_prompt = "Bạn là Trợ lý AI Khí tượng WeatherAI Pro. Trả lời lịch sự, thân thiện và hướng người dùng quay lại các câu hỏi thời tiết nếu họ hỏi lạc đề."
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_question}],
            temperature=0.5
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Lỗi AI: {str(e)}"


def generate_ai_report(user_question, location_name, df_weather, target_hours):
    weather_summary = df_weather.to_string(index=False) if df_weather is not None else ""
    system_prompt = f"Bạn là WeatherAI Intelligence Pro. Phân tích thời tiết tại '{location_name}' cho {target_hours} giờ tới:\n{weather_summary}"
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_question}],
            temperature=0.3
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Lỗi phân tích AI: {str(e)}"

# ==========================================
# 6. ĐIỀU HƯỚNG MÀN HÌNH CHÍNH
# ==========================================

if active_menu == "🛰️ Bản đồ Radar & Vệ tinh":
    st.markdown('<div class="hero-title">🛰️ Bản đồ Radar Mây Mưa Trực Tuyến</div>', unsafe_allow_html=True)
    lat_map, lon_map = 10.8231, 106.6297
    if user_gps and "coords" in user_gps:
        lat_map = user_gps["coords"]["latitude"]
        lon_map = user_gps["coords"]["longitude"]
    windy_url = f"https://embed.windy.com/embed2.html?lat={lat_map}&lon={lon_map}&detailLat={lat_map}&detailLon={lon_map}&width=100%25&height=550&zoom=8&level=surface&overlay=radar&product=radar&menu=&message=true&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=m%2Fs&metricTemp=%C2%B0C&radarRange=-1"
    st.components.v1.iframe(windy_url, height=550, scrolling=False)

elif active_menu == "⚠️ Cảnh báo dông bão":
    st.markdown('<div class="hero-title">⚠️ Cảnh Báo Thời Tiết Cực Đoan</div>', unsafe_allow_html=True)
    data_alert, err = fetch_weather_data("Ho Chi Minh")
    if data_alert:
        st.markdown(f'<div class="safe-box">📍 **Khu vực {data_alert["name"]}**: Hiện không ghi nhận cảnh báo dông bão nguy hiểm trong 24h tới.</div>', unsafe_allow_html=True)

else:
    # Lấy thread hiện tại đang chọn
    active_tid = st.session_state.active_thread_id
    current_thread = st.session_state.threads_store.get(active_tid, {"chats": [], "title": "Cuộc trò chuyện mới"})
    current_chats = current_thread.get("chats", [])

    st.markdown(f'<div class="hero-title">{current_thread.get("title", "WeatherAI Pro")}</div>', unsafe_allow_html=True)

    # Hiển thị lịch sử chat của phiên hiện tại
    for idx, chat in enumerate(current_chats):
        st.markdown(f'<div class="user-msg-card"><b>🗣️ Bạn:</b> {chat["question"]}</div>', unsafe_allow_html=True)

        if chat["type"] == "CHAT":
            st.markdown(f'<div class="ai-card"><b>🤖 WeatherAI:</b><br>{chat["reply"]}</div>', unsafe_allow_html=True)

        elif chat["type"] == "STORM":
            st.markdown(f'<div class="ai-card"><b>🌀 Phân tích Siêu Bão:</b><br>{chat["report"]}</div>', unsafe_allow_html=True)
            windy_storm_url = f"https://embed.windy.com/embed2.html?lat={chat['storm_lat']}&lon={chat['storm_lon']}&detailLat={chat['storm_lat']}&detailLon={chat['storm_lon']}&width=100%25&height=400&zoom=5&level=surface&overlay=wind&product=ecmwf&menu=&message=true&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=m%2Fs&metricTemp=%C2%B0C&radarRange=-1"
            st.components.v1.iframe(windy_storm_url, height=400, scrolling=False)

        elif chat["type"] == "WEATHER":
            data = chat["data"]
            df_full = pd.DataFrame(data["records"])
            num_rows = max(1, chat["target_hours"] // 3)
            df_filtered = df_full.head(num_rows)
            loc_name = data["name"]

            st.markdown(f"📍 **Thời tiết tại {loc_name}** ({data['lat']:.2f}°N, {data['lon']:.2f}°E)")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_filtered["Thời gian"], y=df_filtered["Nhiệt độ (°C)"], mode="lines+markers", name="Nhiệt độ (°C)", line=dict(color="#00C2FF", width=3)))
            fig.add_trace(go.Bar(x=df_filtered["Thời gian"], y=df_filtered["Mưa (mm)"], name="Lượng mưa (mm)", marker_color="rgba(56, 189, 248, 0.5)", yaxis="y2"))
            
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(10, 19, 39, 0.7)",
                margin=dict(l=20, r=20, t=30, b=20),
                height=300,
                xaxis=dict(showgrid=True, fixedrange=True),
                yaxis=dict(title="Nhiệt độ (°C)", fixedrange=True),
                yaxis2=dict(title="Lượng mưa (mm)", overlaying="y", side="right", showgrid=False, fixedrange=True)
            )
            
            st.plotly_chart(fig, use_container_width=True, key=f"fig_{idx}", config={'displayModeBar': False})
            st.markdown(f'<div class="ai-card"><b>🤖 Phân tích WeatherAI:</b><br>{chat["report"]}</div>', unsafe_allow_html=True)

    # Ô nhập liệu chat (Form Submit với Enter)
    st.write("---")
    with st.form(key="chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_q = st.text_input("Nhập địa điểm / câu hỏi:", value="", placeholder="Hỏi WeatherAI (Nhấn Enter để gửi)...", label_visibility="collapsed")
        with col_btn:
            submit_btn = st.form_submit_button("Hỏi AI 🚀", use_container_width=True)

    if submit_btn and user_q.strip():
        query_text = user_q.strip()
        intent_type, loc_target, target_hours = parse_user_intent(query_text)

        new_entry = None

        if intent_type == "CHAT":
            chat_reply = generate_general_chat(query_text)
            new_entry = {"type": "CHAT", "question": query_text, "reply": chat_reply}

        elif intent_type == "STORM":
            storm_lat, storm_lon = 18.0, 115.0
            data, _ = fetch_weather_by_coords(storm_lat, storm_lon)
            report = generate_ai_report(query_text, loc_target, pd.DataFrame(data["records"]), target_hours)
            new_entry = {"type": "STORM", "question": query_text, "location": loc_target, "report": report, "storm_lat": storm_lat, "storm_lon": storm_lon}

        else:
            if loc_target == "USE_GPS" and user_gps and "coords" in user_gps:
                data, err = fetch_weather_by_coords(user_gps["coords"]["latitude"], user_gps["coords"]["longitude"])
            else:
                target_place = loc_target if loc_target != "USE_GPS" else "Ho Chi Minh"
                data, err = fetch_weather_data(target_place)

            if not err and data:
                df = pd.DataFrame(data["records"])
                loc_name = data["name"]
                df_filtered = df.head(max(1, target_hours // 3))
                report = generate_ai_report(query_text, loc_name, df_filtered, target_hours)
                new_entry = {"type": "WEATHER", "question": query_text, "data": data, "target_hours": target_hours, "report": report}

        if new_entry:
            # Nếu đây là câu hỏi đầu tiên của đoạn chat, đặt tiêu đề tự động theo câu hỏi
            if not current_chats:
                current_thread["title"] = query_text[:25] + ("..." if len(query_text) > 25 else "")

            current_chats.append(new_entry)
            current_thread["chats"] = current_chats
            st.session_state.threads_store[active_tid] = current_thread
            
            # Lưu vĩnh viễn vào Web LocalStorage
            save_threads_to_web()

        st.rerun()
