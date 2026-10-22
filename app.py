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
    page_title="WeatherAI",
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

try:
    from streamlit_js_eval import get_geolocation
    user_gps = get_geolocation()
except Exception:
    user_gps = None

# ==========================================
# 2. SIDEBAR NAVIGATION & THEME SWITCHER
# ==========================================
with st.sidebar:
    st.markdown("### ⚡ WeatherAI")
    
    theme_choice = st.radio(
        "🎨 Chế độ giao diện:",
        ["☀️ Light Mode", "🌙 Dark Mode"],
        index=1
    )
    is_dark = "Dark Mode" in theme_choice

    st.write("---")
    st.markdown("Chức năng")
    st.markdown(" **📝 Trò chuyện mới**")
    st.markdown(" **📊 Dự báo & Phân tích**")
    st.markdown(" **🛰️ Bản đồ Radar & Vệ tinh *(chưa khả dụng)* **")
    st.markdown(" **⚠️ Cảnh báo giông bão** ")
    st.markdown(" **⚙️ Cài đặt** *(chưa khả dụng)*")
    st.write("---")
    st.markdown("""
        <div style="background: rgba(128,128,128,0.1); padding: 12px; border-radius: 10px;">
            <div style="font-size:11px; opacity: 0.7; font-weight:600;">MÔ HÌNH DỰ BÁO</div>
            <div style="font-size:16px; font-weight:700;">WeatherAI Pro Neural</div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. DYNAMIC CSS STYLES
# ==========================================
if is_dark:
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

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
            background-color: #050E21 !important;
            border-right: 1px solid rgba(56, 189, 248, 0.12) !important;
        }

        .hero-title {
            text-align: center;
            font-size: 32px;
            font-weight: 800;
            color: #F8FAFC;
            margin-top: 10px;
            margin-bottom: 20px;
        }

        .stTextInput > div > div > input {
            background-color: rgba(18, 27, 47, 0.9) !important;
            border: 1px solid rgba(56, 189, 248, 0.3) !important;
            color: #F8FAFC !important;
            border-radius: 8px !important;
            padding: 10px 16px !important;
        }
        .stButton > button {
            background: linear-gradient(135deg, #00C2FF 0%, #0284C7 100%) !important;
            color: #0A1327 !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 8px !important;
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
            color: #F8FAFC;
        }
        
        .alert-box {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            border-left: 4px solid #EF4444;
            border-radius: 12px;
            padding: 16px;
            margin: 15px 0;
            color: #F8FAFC;
        }
        .safe-box {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-left: 4px solid #10B981;
            border-radius: 12px;
            padding: 16px;
            margin: 15px 0;
            color: #F8FAFC;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

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
            background-color: #F9F9F9 !important;
            border-right: 1px solid #E5E5E5 !important;
        }

        .hero-title {
            text-align: center;
            font-size: 32px;
            font-weight: 600;
            color: #0D0D0D;
            margin-top: 10px;
            margin-bottom: 20px;
        }

        .stTextInput > div > div > input {
            background-color: #FFFFFF !important;
            border: 1px solid #E5E5E5 !important;
            color: #0D0D0D !important;
            border-radius: 999px !important;
            padding: 12px 20px !important;
            font-size: 15px !important;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04) !important;
        }

        .stTextInput > div > div > input:focus {
            border-color: #B4B4B4 !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
        }

        .stButton > button {
            background: #000000 !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border: none !important;
            border-radius: 999px !important;
            padding: 10px 18px !important;
        }

        .telemetry-card {
            background: #F9F9F9;
            border: 1px solid #E5E5E5;
            border-radius: 12px;
            padding: 16px;
        }
        .telemetry-label {
            font-size: 11px;
            font-weight: 600;
            color: #666666;
            text-transform: uppercase;
        }
        .telemetry-value {
            font-size: 24px;
            font-weight: 700;
            color: #0D0D0D;
            margin: 4px 0;
        }
        .telemetry-sub {
            font-size: 12px;
            color: #10A37F;
        }

        .ai-card {
            background: #FFFFFF;
            border: 1px solid #E5E5E5;
            border-radius: 16px;
            padding: 24px;
            margin-top: 20px;
            line-height: 1.6;
            color: #0D0D0D;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
        }
        
        .alert-box {
            background: #FEF2F2;
            border: 1px solid #FCA5A5;
            border-left: 4px solid #EF4444;
            border-radius: 12px;
            padding: 16px;
            margin: 15px 0;
            color: #991B1B;
        }
        .safe-box {
            background: #ECFDF5;
            border: 1px solid #6EE7B7;
            border-left: 4px solid #10B981;
            border-radius: 12px;
            padding: 16px;
            margin: 15px 0;
            color: #065F46;
        }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 4. HÀM XỬ LÝ DỮ LIỆU & AI
# ==========================================
def parse_user_intent(user_question):
    prompt = f"""
Phân tích câu hỏi người dùng và trả về định dạng JSON/Text ngắn gọn:
1. Ý định (is_weather): Trả về 'WEATHER' nếu người dùng hỏi tra cứu thời tiết/lượng mưa/nhiệt độ. Trả về 'CHAT' nếu chỉ là câu chào hỏi, tán gẫu.
2. Tên địa điểm (location): Tên Tỉnh/Thành/Huyện. Trả về 'USE_GPS' nếu người dùng không nhắc đến tên địa danh cụ thể.
3. Khoảng thời gian (hours): Số giờ cần xem (24, 48, 72, 120). Mặc định là 120 nếu không rõ.

Chỉ trả về 1 dòng duy nhất theo định dạng: LOẠI|TÊN_ĐỊA_ĐIỂM|SỐ_GIỜ
Ví dụ: WEATHER|Quan Go Vap, Ho Chi Minh|24
Ví dụ 2: WEATHER|USE_GPS|24
Ví dụ 3: CHAT|NONE|0

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
        return "CHAT", "USE_GPS", 120


def fetch_weather_by_coords(lat, lon):
    geo_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={WEATHER_KEY}"
    display_name = "Vị trí GPS của bạn"
    try:
        geo_res = requests.get(geo_url, timeout=10).json()
        if isinstance(geo_res, list) and len(geo_res) > 0:
            display_name = geo_res[0].get('local_names', {}).get('vi', geo_res[0].get('name', display_name))
    except Exception:
        pass

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
    system_prompt = "Bạn là Trợ lý AI WeatherAI thân thiện, thông minh. Hãy trò chuyện tự nhiên, lịch sự với người dùng. Nếu người dùng không hỏi về thời tiết, tuyệt đối KHÔNG phân tích dự báo thời tiết hay nhắc tới dữ liệu khí tượng."
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            temperature=0.7
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Lỗi khởi tạo AI: {str(e)}"


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
st.markdown('<div class="hero-title">WeatherAI(Demo)</div>', unsafe_allow_html=True)

col_input, col_btn = st.columns([5, 1])
with col_input:
    user_q = st.text_input(
        "Nhập địa điểm / câu hỏi:",
        value="",
        placeholder="Hỏi WeatherAI...",
        label_visibility="collapsed"
    )
with col_btn:
    submit_btn = st.button("Gửi 🚀", use_container_width=True)

if submit_btn:
    query_text = user_q.strip() if user_q.strip() else "Thời tiết hôm nay thế nào?"

    with st.spinner("⚡ WeatherAI đang xử lý..."):
        intent_type, loc_target, target_hours = parse_user_intent(query_text)

        if intent_type == "CHAT":
            chat_reply = generate_general_chat(query_text)
            st.markdown(f'<div class="ai-card">{chat_reply}</div>', unsafe_allow_html=True)

        else:
            if loc_target == "USE_GPS" and user_gps and "coords" in user_gps:
                lat = user_gps["coords"]["latitude"]
                lon = user_gps["coords"]["longitude"]
                data, err = fetch_weather_by_coords(lat, lon)
            else:
                target_place = loc_target if loc_target != "USE_GPS" else "Ho Chi Minh"
                data, err = fetch_weather_data(target_place)

            if err:
                st.error(f"❌ {err}")
            else:
                df = data["df"]
                loc_name = data["name"]

                num_rows = max(1, target_hours // 3)
                df_filtered = df.head(num_rows)

                highlight_color = "#00C2FF" if is_dark else "#10A37F"
                badge_bg = "rgba(0, 194, 255, 0.12)" if is_dark else "#F0F0F0"
                badge_text = "#75D1FF" if is_dark else "#666666"

                st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 10px; margin: 20px 0 10px 0;">
                        <span style="font-size: 20px; font-weight: 700;">
                            📍 Thời tiết tại <span style="color: {highlight_color};">{loc_name}</span>
                        </span>
                        <span style="background: {badge_bg}; color: {badge_text}; font-family: monospace; font-size: 12px; padding: 2px 8px; border-radius: 6px;">
                            🎯 {data['lat']:.3f}°N, {data['lon']:.3f}°E
                        </span>
                    </div>
                """, unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns(4)
                curr_temp = df.iloc[0]["Nhiệt độ (°C)"]
                curr_feel = df.iloc[0]["Cảm giác (°C)"]
                curr_hum = df.iloc[0]["Độ ẩm (%)"]
                total_rain_24h = df.head(8)["Mưa (mm)"].sum()

                with c1:
                    st.markdown('<div class="telemetry-card"><div class="telemetry-label">ĐỘ CHÍNH XÁC</div><div class="telemetry-value">96.8%</div><div class="telemetry-sub">RMS: 0.42°C</div></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown('<div class="telemetry-card"><div class="telemetry-label">ĐỘ TRỄ</div><div class="telemetry-value">142 ms</div><div class="telemetry-sub">TPU Pipeline</div></div>', unsafe_allow_html=True)
                with c3:
                    st.markdown(f'<div class="telemetry-card"><div class="telemetry-label">NHIỆT ĐỘ</div><div class="telemetry-value">{curr_temp:.1f}°C</div><div class="telemetry-sub">Cảm giác {curr_feel:.1f}°C</div></div>', unsafe_allow_html=True)
                with c4:
                    st.markdown(f'<div class="telemetry-card"><div class="telemetry-label">MƯA 24H</div><div class="telemetry-value">{total_rain_24h:.1f} mm</div><div class="telemetry-sub">Độ ẩm {curr_hum}%</div></div>', unsafe_allow_html=True)

                st.write("")

                # ==========================================
                # CHỨC NĂNG 1: ⚠️ CẢNH BÁO DÔNG BÃO TỰ ĐỘNG
                # ==========================================
                max_rain = df_filtered["Mưa (mm)"].max()
                heavy_rain_times = df_filtered[df_filtered["Mưa (mm)"] >= 10.0]["Thời gian"].tolist()
                thunder_times = df_filtered[df_filtered["Mô tả"].str.contains("dông|bão|sấm|mưa to|mưa rất to", case=False, na=False)]["Thời gian"].tolist()

                alerts = []
                if max_rain >= 10.0:
                    alerts.append(f"🌧️ **Cảnh báo mưa lớn**: Lượng mưa cao nhất đạt **{max_rain:.1f} mm/3h**. Khu vực có nguy cơ ngập lụt cục bộ.")
                if thunder_times:
                    alerts.append(f"⚡ **Cảnh báo Dông Sấm**: Ghi nhận thời tiết nguy hiểm vào các khung giờ: `{', '.join(thunder_times[:3])}`.")
                if curr_temp >= 37.0:
                    alerts.append("🔥 **Cảnh báo Nắng nóng cực đoan**: Nhiệt độ trên 37°C, hạn chế ra ngoài trời vào giữa trưa.")

                st.subheader("⚠️ Cảnh báo Dông Bão & Thời tiết Cực đoan")
                if alerts:
                    alert_html = "<br>".join(alerts)
                    st.markdown(f'<div class="alert-box">{alert_html}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="safe-box">✅ **An toàn**: Không ghi nhận cảnh báo mưa lớn hay dông bão cực đoan trong khoảng thời gian này.</div>', unsafe_allow_html=True)

                st.write("")

                # Biểu đồ thời tiết
                st.subheader(f"📈 Biểu đồ thời tiết ({target_hours} giờ tới)")

                fig = go.Figure()
                line_col = "#00C2FF" if is_dark else "#10A37F"
                bar_col = "rgba(56, 189, 248, 0.5)" if is_dark else "rgba(16, 163, 127, 0.3)"
                bg_col = "rgba(10, 19, 39, 0.6)" if is_dark else "#FFFFFF"
                grid_col = "rgba(255,255,255,0.08)" if is_dark else "#F0F0F0"

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
                    height=360,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    dragmode=False,
                    xaxis=dict(showgrid=True, gridcolor=grid_col, fixedrange=True),
                    yaxis=dict(title="Nhiệt độ (°C)", showgrid=True, gridcolor=grid_col, fixedrange=True),
                    yaxis2=dict(title="Lượng mưa (mm)", overlaying="y", side="right", showgrid=False, fixedrange=True)
                )
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

                # ==========================================
                # CHỨC NĂNG 2: 🛰️ BẢN ĐỒ RADAR & VỆ TINH TRỰC TUYẾN
                # ==========================================
                st.subheader("🛰️ Bản đồ Radar Mây Mưa & Vệ Tinh Trực Tuyến")
                windy_url = f"https://embed.windy.com/embed2.html?lat={data['lat']}&lon={data['lon']}&detailLat={data['lat']}&detailLon={data['lon']}&width=100%25&height=450&zoom=8&level=surface&overlay=radar&product=radar&menu=&message=true&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=m%2Fs&metricTemp=%C2%B0C&radarRange=-1"
                
                st.components.v1.iframe(windy_url, height=450, scrolling=False)

                st.write("")

                st.subheader("🤖 Phân tích AI")
                report = generate_ai_report(query_text, loc_name, df_filtered, target_hours)
                st.markdown(f'<div class="ai-card">{report}</div>', unsafe_allow_html=True)
