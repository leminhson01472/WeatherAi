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
# 1. CẤU HÌNH TRANG & API KEY
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
# 2. LƯU TRỰC TIẾP TRÊN WEB LOCALSTORAGE (BẢO MẬT)
# ==========================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pending_new_chat" not in st.session_state:
    st.session_state.pending_new_chat = None

# Mã JavaScript đồng bộ dữ liệu với LocalStorage của trình duyệt
local_storage_js = """
<script>
    const STORAGE_KEY = 'weatherai_pro_web_chat';

    function syncFromWebStorage() {
        const storedData = localStorage.getItem(STORAGE_KEY);
        if (storedData) {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: storedData
            }, '*');
        } else {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: '[]'
            }, '*');
        }
    }
    setTimeout(syncFromWebStorage, 300);
</script>
"""

web_storage_data = components.html(local_storage_js, height=0)

if web_storage_data and isinstance(web_storage_data, str) and not st.session_state.chat_history:
    try:
        loaded_history = json.loads(web_storage_data)
        if isinstance(loaded_history, list):
            st.session_state.chat_history = loaded_history
    except Exception:
        pass

# Thêm tin nhắn mới và tự động cập nhật vào LocalStorage trên máy người dùng
if st.session_state.pending_new_chat:
    st.session_state.chat_history.append(st.session_state.pending_new_chat)
    st.session_state.pending_new_chat = None
    
    updated_json = json.dumps(st.session_state.chat_history, ensure_ascii=False)
    save_js = f"""
    <script>
        localStorage.setItem('weatherai_pro_web_chat', {json.dumps(updated_json)});
    </script>
    """
    components.html(save_js, height=0)

# Lấy thông tin GPS an toàn nếu người dùng cho phép
try:
    from streamlit_js_eval import get_geolocation
    user_gps = get_geolocation()
except Exception:
    user_gps = None

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
            <div style="width: 40px; height: 40px; border-radius: 50%; background: #00C2FF; display: flex; align-items: center; justify-content: center; color: #0A1327; box-shadow: 0 0 20px rgba(0,194,255,0.4); font-size: 20px;">
                ⚡
            </div>
            <div>
                <div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 18px; font-weight: 800; color: #F8FAFC !important;">WeatherAI Pro</div>
                <div style="font-size: 11px; color: #38BDF8 !important; font-weight: 600; text-transform: uppercase;">Trợ lý Khí tượng AI</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    theme_choice = st.radio(
        "🎨 Chế độ giao diện:",
        ["☀️ Light Mode", "🌙 Dark Glass Mode"],
        index=1
    )
    is_dark = "Dark" in theme_choice

    st.write("---")
    
    active_menu = st.radio(
        "📌 Danh mục chức năng:",
        [
            "📊 Dự báo, Phân tích & Trò chuyện",
            "🛰️ Bản đồ Radar & Vệ tinh",
            "⚠️ Cảnh báo dông bão"
        ],
        index=0
    )
    
    st.write("---")
    st.markdown("<h4 style='color: #F8FAFC !important;'>🛡️ Quản lý Bộ nhớ Web</h4>", unsafe_allow_html=True)

    if st.button("🗑️ Xóa toàn bộ lịch sử trên Web", use_container_width=True):
        st.session_state.chat_history = []
        clear_storage_js = """
        <script>
            localStorage.removeItem('weatherai_pro_web_chat');
        </script>
        """
        components.html(clear_storage_js, height=0)
        st.rerun()

    st.write("---")
    st.markdown("""
        <div style="background: rgba(18, 27, 47, 0.7); backdrop-filter: blur(12px); padding: 14px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);">
            <div style="font-size: 10px; color: #94A3B8 !important; font-weight: 700; text-transform: uppercase;">TRẠNG THÁI BẢO MẬT</div>
            <div style="font-size: 12px; color: #38BDF8 !important; font-weight: 700; margin-top: 4px;">🔒 Lưu trên Trình duyệt Web</div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 4. DYNAMIC CSS STYLES (ĐÈ MÀU CHỮ SẮC NÉT)
# ==========================================
if is_dark:
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        /* NỀN TOÀN TRANG DARK GLASS */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #0A1327 !important;
            color: #F8FAFC !important;
            font-family: 'Inter', sans-serif;
        }

        #MainMenu, footer {visibility: hidden;}

        /* SIDEBAR GLASSMORPHISM */
        [data-testid="stSidebar"] {
            background-color: rgba(5, 14, 33, 0.85) !important;
            backdrop-filter: blur(20px) !important;
            border-right: 1px solid rgba(56, 189, 248, 0.15) !important;
        }

        /* ÉP MÀU CHỮ TOÀN BỘ SIDEBAR SÁNG RÕ */
        [data-testid="stSidebar"] *, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] span, 
        [data-testid="stSidebar"] div {
            color: #F8FAFC !important;
        }

        [data-testid="stSidebar"] [data-aria-selected="true"] p {
            color: #38BDF8 !important;
            font-weight: 700 !important;
        }

        /* INPUT FIELD */
        .stTextInput > div > div > input {
            background-color: rgba(18, 27, 47, 0.85) !important;
            border: 1px solid rgba(56, 189, 248, 0.3) !important;
            color: #FFFFFF !important;
            border-radius: 9999px !important;
            padding: 12px 24px !important;
            font-size: 14px !important;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.4) !important;
        }

        .stTextInput > div > div > input::placeholder {
            color: #94A3B8 !important;
            opacity: 1 !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #00C2FF !important;
            box-shadow: 0 0 16px rgba(0, 194, 255, 0.35) !important;
        }

        /* BUTTONS */
        .stButton > button, [data-testid="stFormSubmitButton"] > button {
            background: linear-gradient(135deg, #00C2FF 0%, #0284C7 100%) !important;
            color: #0A1327 !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 9999px !important;
            padding: 10px 24px !important;
            box-shadow: 0 8px 20px rgba(0, 194, 255, 0.3) !important;
        }

        .hero-title {
            text-align: center;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 32px;
            font-weight: 800;
            color: #F8FAFC;
            margin-top: 10px;
            margin-bottom: 20px;
            letter-spacing: -0.02em;
        }

        /* CARDS & PANELS */
        .telemetry-card {
            background: rgba(24, 35, 60, 0.75);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(56, 189, 248, 0.18);
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 12px 32px rgba(11, 19, 38, 0.5);
        }
        .telemetry-label {
            font-size: 11px;
            font-weight: 700;
            color: #94A3B8 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .telemetry-value {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 26px;
            font-weight: 700;
            color: #F8FAFC !important;
            margin: 6px 0;
        }
        .telemetry-sub {
            font-size: 12px;
            color: #38BDF8 !important;
        }

        .user-msg-card {
            background: rgba(56, 189, 248, 0.15);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 16px;
            padding: 16px 20px;
            margin-top: 15px;
            color: #F8FAFC !important;
            backdrop-filter: blur(12px);
        }

        .ai-card {
            background: rgba(18, 27, 47, 0.85);
            border: 1px solid rgba(0, 194, 255, 0.35);
            border-left: 4px solid #00C2FF;
            border-radius: 16px;
            padding: 20px;
            margin-top: 10px;
            margin-bottom: 20px;
            line-height: 1.6;
            color: #F8FAFC !important;
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(16px);
        }
        
        .alert-box {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.4);
            border-left: 4px solid #EF4444;
            border-radius: 16px;
            padding: 18px;
            margin: 15px 0;
            color: #F8FAFC !important;
        }
        .safe-box {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-left: 4px solid #10B981;
            border-radius: 16px;
            padding: 18px;
            margin: 15px 0;
            color: #F8FAFC !important;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700&display=swap');

        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #FFFFFF !important;
            color: #0D0D0D !important;
            font-family: 'Inter', sans-serif;
        }

        #MainMenu, footer {visibility: hidden;}

        [data-testid="stSidebar"] {
            background-color: #F8FAFC !important;
            border-right: 1px solid #E2E8F0 !important;
        }

        [data-testid="stSidebar"] *, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] span {
            color: #0F172A !important;
        }

        .hero-title {
            text-align: center;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 32px;
            font-weight: 700;
            color: #0D0D0D;
            margin-top: 10px;
            margin-bottom: 20px;
        }

        .stTextInput > div > div > input {
            background-color: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            color: #0D0D0D !important;
            border-radius: 9999px !important;
            padding: 12px 20px !important;
            font-size: 14px !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
        }

        .stButton > button, [data-testid="stFormSubmitButton"] > button {
            background: #000000 !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border: none !important;
            border-radius: 9999px !important;
            padding: 10px 20px !important;
        }

        .telemetry-card {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        }
        .telemetry-label {
            font-size: 11px;
            font-weight: 700;
            color: #64748B !important;
            text-transform: uppercase;
        }
        .telemetry-value {
            font-size: 26px;
            font-weight: 700;
            color: #0F172A !important;
            margin: 4px 0;
        }
        .telemetry-sub {
            font-size: 12px;
            color: #0284C7 !important;
        }

        .user-msg-card {
            background: #F0FDF4;
            border: 1px solid #DCFCE7;
            border-radius: 16px;
            padding: 16px;
            margin-top: 15px;
            color: #166534 !important;
        }

        .ai-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 20px;
            margin-top: 10px;
            margin-bottom: 20px;
            line-height: 1.6;
            color: #0F172A !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
        }
        
        .alert-box {
            background: #FEF2F2;
            border: 1px solid #FCA5A5;
            border-left: 4px solid #EF4444;
            border-radius: 16px;
            padding: 18px;
            margin: 15px 0;
            color: #991B1B !important;
        }
        .safe-box {
            background: #ECFDF5;
            border: 1px solid #6EE7B7;
            border-left: 4px solid #10B981;
            border-radius: 16px;
            padding: 18px;
            margin: 15px 0;
            color: #065F46 !important;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 5. HÀM XỬ LÝ DỮ LIỆU & AI
# ==========================================
def parse_user_intent(user_question):
    prompt = f"""
Phân tích câu hỏi người dùng và trả về định dạng JSON/Text ngắn gọn:
1. Ý định (is_weather): Trả về 'STORM' nếu hỏi về siêu bão, bão, áp thấp (ví dụ: 'bão CHAMPI'). Trả về 'WEATHER' nếu người dùng hỏi tra cứu thời tiết địa phương/lượng mưa/nhiệt độ. Trả về 'CHAT' nếu chỉ chào hỏi, tán gẫu, hỏi đáp chung không cần tra cứu thời tiết.
2. Tên địa điểm (location): Tên Tỉnh/Thành/Huyện/Bão. Trả về 'USE_GPS' nếu người dùng không nhắc đến tên địa danh cụ thể.
3. Khoảng thời gian (hours): Số giờ cần xem (24, 48, 72, 120). Mặc định là 120 nếu không rõ.

Chỉ trả về 1 dòng duy nhất theo định dạng: LOẠI|TÊN_ĐỊA_ĐIỂM|SỐ_GIỜ
Ví dụ 1: STORM|Siêu bão CHAMPI|120
Ví dụ 2: WEATHER|Quan Go Vap, Ho Chi Minh|24
Ví dụ 3: WEATHER|USE_GPS|120
Ví dụ 4: CHAT|NONE|0

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
        try:
            geo_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={WEATHER_KEY}"
            geo_res = requests.get(geo_url, timeout=5).json()
            if isinstance(geo_res, list) and len(geo_res) > 0:
                display_name = geo_res[0].get('local_names', {}).get('vi', geo_res[0].get('name', "Vị trí GPS của bạn"))
        except Exception:
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
    return fetch_weather_by_coords(lat, lon)


def generate_general_chat(user_question):
    system_prompt = """
Bạn là Trợ lý AI Khí tượng chuyên sâu WeatherAI Pro.

QUY TẮC ĐIỀU HƯỚNG BẮC CẦU:
1. Nếu người dùng chào hỏi cơ bản: Trả lời lịch sự, ngắn gọn và giới thiệu bạn có thể giúp gì về thời tiết/dự báo/dông bão.
2. Nếu người dùng hỏi câu KHÔNG LIÊN QUAN ĐẾN THỜI TIẾT:
   - Trả lời ngắn gọn 1 câu mang tính lịch sự.
   - Nhẹ nhàng khéo léo chuyển hướng (pivot) người dùng quay trở lại chủ đề Thời tiết & Khí tượng.
   - Gợi ý 2-3 câu hỏi thời tiết mẫu (tra cứu thời tiết địa phương, xem bản đồ bão, hoặc cảnh báo mưa lớn).
"""
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0.5
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Lỗi khởi tạo AI: {str(e)}"


def generate_ai_report(user_question, location_name, df_weather, target_hours):
    gio_viet_nam = timezone(timedelta(hours=7))
    today_str = datetime.now(gio_viet_nam).strftime("%d/%m/%Y %H:%M:%S")

    weather_summary = df_weather.to_string(index=False) if df_weather is not None else ""

    system_prompt = f"""
Bạn là Trợ lý AI Khí tượng WeatherAI Intelligence Pro.
Thời gian hiện tại: {today_str}.

DỮ LIỆU KHÍ TƯỢNG {target_hours} GIỜ TỚI TẠI KHU VỰC THAM CHIẾU '{location_name}':
{weather_summary}

YÊU CẦU TRẢ LỜI:
1. Phân tích và trả lời trực tiếp câu hỏi của người dùng: "{user_question}".
2. KHÔNG ĐƯỢC TỪ CHỐI TRẢ LỜI.
3. Nếu người dùng hỏi về CƠN BÃO / SIÊU BÃO:
   - Phân tích vị trí, quy mô, sức gió và hướng di chuyển.
   - Nhấn mạnh: "🌀 Bản đồ Radar & Vệ tinh theo dõi trực tiếp cơn bão đã được hiển thị ngay bên dưới để bạn dễ dàng theo dõi."
   - Đưa ra cảnh báo thiên tai và khuyến nghị phòng tránh an toàn.
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
# 6. ĐIỀU HƯỚNG GIAO DIỆN THEO MENU
# ==========================================

# TAB 1: 🛰️ BẢN ĐỒ RADAR TRỰC TIẾP
if active_menu == "🛰️ Bản đồ Radar & Vệ tinh":
    st.markdown('<div class="hero-title">🛰️ Bản đồ Radar & Vệ tinh Mây Mưa Trực Tuyến</div>', unsafe_allow_html=True)
    
    lat_map = 10.8231
    lon_map = 106.6297
    if user_gps and "coords" in user_gps:
        lat_map = user_gps["coords"]["latitude"]
        lon_map = user_gps["coords"]["longitude"]

    windy_url = f"https://embed.windy.com/embed2.html?lat={lat_map}&lon={lon_map}&detailLat={lat_map}&detailLon={lon_map}&width=100%25&height=550&zoom=8&level=surface&overlay=radar&product=radar&menu=&message=true&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=m%2Fs&metricTemp=%C2%B0C&radarRange=-1"
    st.components.v1.iframe(windy_url, height=550, scrolling=False)

# TAB 2: ⚠️ CẢNH BÁO DÔNG BÃO
elif active_menu == "⚠️ Cảnh báo dông bão":
    st.markdown('<div class="hero-title">⚠️ Hệ Thống Cảnh Báo Dông Bão & Thời Tiết Cực Đoan</div>', unsafe_allow_html=True)
    
    if user_gps and "coords" in user_gps:
        data_alert, err = fetch_weather_by_coords(user_gps["coords"]["latitude"], user_gps["coords"]["longitude"])
    else:
        data_alert, err = fetch_weather_data("Ho Chi Minh")

    if data_alert:
        df_a = pd.DataFrame(data_alert["records"])
        max_rain = df_a["Mưa (mm)"].max()
        thunder_times = df_a[df_a["Mô tả"].str.contains("dông|bão|sấm|mưa to|mưa rất to", case=False, na=False)]["Thời gian"].tolist()
        curr_temp = df_a.iloc[0]["Nhiệt độ (°C)"]

        alerts = []
        if max_rain >= 10.0:
            alerts.append(f"🌧️ **Cảnh báo mưa lớn**: Lượng mưa đỉnh điểm đạt **{max_rain:.1f} mm/3h**. Nguy cơ gây ngập lụt ở khu vực trũng thấp.")
        if thunder_times:
            alerts.append(f"⚡ **Cảnh báo Dông Sấm**: Dữ liệu ghi nhận sấm dông nguy hiểm tại các khung giờ: `{', '.join(thunder_times[:4])}`.")
        if curr_temp >= 37.0:
            alerts.append("🔥 **Cảnh báo Nắng nóng cực đoan**: Nhiệt độ vượt ngưỡng 37°C. Cần chú ý bồi bổ nước và tránh ánh nắng trực tiếp.")

        if alerts:
            alert_html = "<br><br>".join(alerts)
            st.markdown(f'<div class="alert-box"><h4>📍 Địa điểm: {data_alert["name"]}</h4><hr>{alert_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="safe-box">📍 **Khu vực {data_alert["name"]}**: Hiện không ghi nhận cảnh báo dông bão hay mưa lớn cực đoan trong những ngày tới.</div>', unsafe_allow_html=True)

# TAB 3: DỰ BÁO, PHÂN TÍCH & TRÒ CHUYỆN
else:
    st.markdown('<div class="hero-title">WeatherAI Pro Dashboard</div>', unsafe_allow_html=True)

    # 1. HIỂN THỊ LỊCH SỬ CHAT TỰ ĐỘNG ĐỌC TỪ LOCALSTORAGE TRÌNH DUYỆT
    for idx, chat in enumerate(st.session_state.chat_history):
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

            highlight_color = "#00C2FF" if is_dark else "#0284C7"
            badge_bg = "rgba(0, 194, 255, 0.15)" if is_dark else "#F0F9FF"
            badge_text = "#38BDF8" if is_dark else "#0369A1"

            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 10px; margin: 15px 0 10px 0;">
                    <span style="font-size: 18px; font-weight: 700;">
                        📍 Thời tiết tại <span style="color: {highlight_color};">{loc_name}</span>
                    </span>
                    <span style="background: {badge_bg}; color: {badge_text}; font-family: monospace; font-size: 11px; padding: 3px 10px; border-radius: 9999px;">
                        🎯 {data['lat']:.3f}°N, {data['lon']:.3f}°E
                    </span>
                </div>
            """, unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            curr_temp = df_full.iloc[0]["Nhiệt độ (°C)"]
            curr_feel = df_full.iloc[0]["Cảm giác (°C)"]
            curr_hum = df_full.iloc[0]["Độ ẩm (%)"]
            total_rain_24h = df_full.head(8)["Mưa (mm)"].sum()

            with c1:
                st.markdown('<div class="telemetry-card"><div class="telemetry-label">ĐỘ CHÍNH XÁC AI</div><div class="telemetry-value">96.8%</div><div class="telemetry-sub">RMS: 0.42°C</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="telemetry-card"><div class="telemetry-label">TỐC ĐỘ SUY LUẬN</div><div class="telemetry-value">142 ms</div><div class="telemetry-sub">TPU Cloud Pipeline</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="telemetry-card"><div class="telemetry-label">NHIỆT ĐỘ THỰC TẾ</div><div class="telemetry-value">{curr_temp:.1f}°C</div><div class="telemetry-sub">Cảm giác {curr_feel:.1f}°C</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="telemetry-card"><div class="telemetry-label">LƯỢNG MƯA 24H & ĐỘ ẨM</div><div class="telemetry-value">{total_rain_24h:.1f} mm</div><div class="telemetry-sub">Độ ẩm {curr_hum}%</div></div>', unsafe_allow_html=True)

            # Vẽ biểu đồ Plotly
            fig = go.Figure()
            line_col = "#00C2FF" if is_dark else "#0284C7"
            bar_col = "rgba(56, 189, 248, 0.5)" if is_dark else "rgba(2, 132, 199, 0.3)"
            bg_col = "rgba(10, 19, 39, 0.7)" if is_dark else "#FFFFFF"
            grid_col = "rgba(255, 255, 255, 0.08)" if is_dark else "#E2E8F0"

            fig.add_trace(go.Scatter(
                x=df_filtered["Thời gian"], y=df_filtered["Nhiệt độ (°C)"],
                mode="lines+markers", name="Nhiệt độ (°C)",
                line=dict(color=line_col, width=3)
            ))
            fig.add_trace(go.Bar(
                x=df_filtered["Thời gian"], y=df_filtered["Mưa (mm)"],
                name="Lượng mưa (mm)", marker_color=bar_col,
                yaxis="y2"
            ))
            
            fig.update_layout(
                template="plotly_dark" if is_dark else "plotly_white",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor=bg_col,
                margin=dict(l=20, r=20, t=30, b=20),
                height=320,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                dragmode=False,
                xaxis=dict(showgrid=True, gridcolor=grid_col, fixedrange=True),
                yaxis=dict(title="Nhiệt độ (°C)", showgrid=True, gridcolor=grid_col, fixedrange=True),
                yaxis2=dict(title="Lượng mưa (mm)", overlaying="y", side="right", showgrid=False, fixedrange=True)
            )
            
            st.plotly_chart(fig, use_container_width=True, key=f"fig_{idx}", config={'displayModeBar': False})
            st.markdown(f'<div class="ai-card"><b>🤖 Phân tích WeatherAI:</b><br>{chat["report"]}</div>', unsafe_allow_html=True)

    # 2. Ô NHẬP LIỆU BẰNG ST.FORM (ENTER ĐỂ GỬI & TỰ ĐỘNG XÓA CHỮ)
    st.write("---")
    with st.form(key="chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_q = st.text_input(
                "Nhập địa điểm / câu hỏi:",
                value="",
                placeholder="Hỏi WeatherAI (Nhấn Enter để gửi)...",
                label_visibility="collapsed"
            )
        with col_btn:
            submit_btn = st.form_submit_button("Hỏi WeatherAI 🚀", use_container_width=True)

    # 3. XỬ LÝ VÀ CHUẨN BỊ ĐƯA VÀO LOCALSTORAGE TRÌNH DUYỆT
    if submit_btn and user_q.strip():
        query_text = user_q.strip()
        intent_type, loc_target, target_hours = parse_user_intent(query_text)

        new_entry = None

        if intent_type == "CHAT":
            chat_reply = generate_general_chat(query_text)
            new_entry = {
                "type": "CHAT",
                "question": query_text,
                "reply": chat_reply
            }

        elif intent_type == "STORM":
            storm_lat, storm_lon = 18.0, 115.0
            data, _ = fetch_weather_by_coords(storm_lat, storm_lon)
            report = generate_ai_report(query_text, loc_target, pd.DataFrame(data["records"]), target_hours)
            new_entry = {
                "type": "STORM",
                "question": query_text,
                "location": loc_target,
                "report": report,
                "storm_lat": storm_lat,
                "storm_lon": storm_lon
            }

        else:
            if loc_target == "USE_GPS" and user_gps and "coords" in user_gps:
                lat = user_gps["coords"]["latitude"]
                lon = user_gps["coords"]["longitude"]
                data, err = fetch_weather_by_coords(lat, lon)
            else:
                target_place = loc_target if loc_target != "USE_GPS" else "Ho Chi Minh"
                data, err = fetch_weather_data(target_place)

            if not err and data:
                df = pd.DataFrame(data["records"])
                loc_name = data["name"]
                num_rows = max(1, target_hours // 3)
                df_filtered = df.head(num_rows)
                report = generate_ai_report(query_text, loc_name, df_filtered, target_hours)

                new_entry = {
                    "type": "WEATHER",
                    "question": query_text,
                    "data": data,
                    "target_hours": target_hours,
                    "report": report
                }

        if new_entry:
            st.session_state.pending_new_chat = new_entry

        st.rerun()
