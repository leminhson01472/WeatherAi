import os
import requests
from datetime import datetime, timezone, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# 1. CẤU HÌNH HỆ THỐNG & API KEY
load_dotenv()
AI_KEY = os.getenv("APIGIARE_API_KEY")
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

if not AI_KEY:
    st.error("❌ Thiếu APIGIARE_API_KEY trong file .env")
    st.stop()

if not WEATHER_KEY:
    st.error("❌ Thiếu OPENWEATHER_API_KEY trong file .env")
    st.stop()

client = OpenAI(
    api_key=AI_KEY,
    base_url="https://api.apigiare.vn/v1",
    timeout=60,
    max_retries=2,
)

MODEL = "gpt-4o"

# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="Trợ lý AI Dự báo Thời tiết Thông minh",
    page_icon="🌤️",
    layout="wide"
)


# 2. CÁC HÀM XỬ LÝ THỜI TIẾT & AI

def extract_location_from_prompt(user_question):
    """Dùng AI để trích xuất tên địa điểm/thành phố từ câu hỏi của người dùng."""
    gio_viet_nam = timezone(timedelta(hours=7))
    today_str = datetime.now(gio_viet_nam).strftime("%d/%m/%Y %H:%M:%S")

    prompt = f"""
Hãy trích xuất tên địa điểm/thành phố/quận/huyện từ câu hỏi của người dùng để tra cứu thời tiết.
Nếu không đề cập địa điểm nào, hãy trả về 'Ho Chi Minh'.
Thời gian hiện tại: {today_str}.

Ví dụ:
- '5 ngày tới Gò Vấp có mưa không?' -> 'Go Vap, Ho Chi Minh'
- 'Thời tiết Hà Nội hôm nay' -> 'Ha Noi'
- 'Ngày mai trời thế nào?' -> 'Ho Chi Minh'

Câu hỏi: {user_question}
Chỉ trả về DUY NHẤT tên địa điểm bằng tiếng Anh hoặc tiếng Việt không dấu.
"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    return response.choices[0].message.content.strip()


def get_weather_forecast(location_name):
    """Gọi OpenWeatherMap API lấy dự báo thời tiết 5 ngày (mỗi 3 giờ)."""
    # Bước 1: Lấy tọa độ (Geocoding)
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location_name},VN&limit=1&appid={WEATHER_KEY}"
    geo_res = requests.get(geo_url, timeout=10).json()

    if not geo_res:
        # Thử lại không gắn mã quốc gia VN
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location_name}&limit=1&appid={WEATHER_KEY}"
        geo_res = requests.get(geo_url, timeout=10).json()

    if not geo_res:
        return None, f"Không tìm thấy tọa độ cho địa điểm: '{location_name}'"

    lat = geo_res[0]['lat']
    lon = geo_res[0]['lon']
    display_name = geo_res[0].get('local_names', {}).get('vi', geo_res[0]['name'])

    # Bước 2: Lấy dữ liệu dự báo 5 ngày (3-hour forecast)
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric&lang=vi"
    forecast_res = requests.get(forecast_url, timeout=10).json()

    if forecast_res.get("cod") != "200":
        return None, "Lỗi khi kết nối tới dịch vụ thời tiết."

    # Xử lý chuẩn hóa dữ liệu thành DataFrame
    records = []
    for item in forecast_res["list"]:
        rain_vol = item.get("rain", {}).get("3h", 0)  # Lượng mưa 3h (mm)
        records.append({
            "Thời gian": item["dt_txt"],
            "Nhiệt độ (°C)": item["main"]["temp"],
            "Cảm giác như (°C)": item["main"]["feels_like"],
            "Độ ẩm (%)": item["main"]["humidity"],
            "Lượng mưa (mm)": rain_vol,
            "Mô tả": item["weather"][0]["description"].capitalize()
        })

    df = pd.DataFrame(records)
    return {"name": display_name, "df": df, "raw": forecast_res}, None


def generate_weather_analysis(user_question, location_name, df_weather):
    """Dùng GPT-4o phân tích dữ liệu thời tiết thực tế và trả lời câu hỏi."""
    gio_viet_nam = timezone(timedelta(hours=7))
    today_str = datetime.now(gio_viet_nam).strftime("%d/%m/%Y %H:%M:%S")

    weather_summary = df_weather.to_string(index=False)

    system_prompt = f"""
Bạn là Trợ lý AI Dự báo Thời tiết chuyên nghiệp, thân thiện và chính xác.
Thời gian thực tế hiện tại (UTC+7): {today_str}.

DƯỚI ĐÂY LÀ DỮ LIỆU THỜI TIẾT THỰC TẾ DỰ BÁO 5 NGÀY TẠI '{location_name}':
{weather_summary}

YÊU CẦU:
1. Trả lời trực tiếp và chính xác câu hỏi của người dùng dựa hoàn toàn vào dữ liệu trên.
2. Nếu người dùng hỏi về lượng mưa, hãy tổng hợp ngày nào mưa nhiều nhất, khung giờ nào mưa.
3. Đưa ra lời khuyên hữu ích (mang theo ô/áo mưa, trang phục, thời điểm di chuyển phù hợp).
4. Giữ phong cách trả lời ngắn gọn, rõ ràng, trình bày bằng Markdown có emoji sinh động.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()


# 3. GIAO DIỆN NGƯỜI DÙNG (STREAMLIT)

st.title("🌤️ Trợ lý AI Dự báo Thời tiết (Real-time Weather AI)")
st.caption(
    "Nhập câu hỏi tự nhiên -> Tự động xác định vị trí & lấy dữ liệu OpenWeatherMap -> AI Phân tích & Trực quan hóa")

# Sidebar
with st.sidebar:
    st.header("⚙️ Dịch vụ Thời tiết")
    st.success("✅ Đã kết nối OpenWeatherMap API")
    st.info(
        "💡 **Gợi ý câu hỏi:**\n"
        "- 5 ngày tiếp theo, ngày nào có nhiều mưa nhất ở Gò Vấp?\n"
        "- Cuối tuần này thời tiết Hà Nội ra sao?\n"
        "- Hôm nay ở Đà Nẵng có nên đi chơi ngoài trời không?"
    )

# Khung nhập câu hỏi
user_question = st.text_input(
    "💬 Nhập câu hỏi thời tiết của bạn:",
    placeholder="Ví dụ: 5 ngày tiếp theo, ngày nào có nhiều mưa nhất ở Quận Gò Vấp, TP.HCM?"
)

if st.button("🚀 Dự báo & Phân tích", type="primary") and user_question:
    with st.spinner("AI đang xác định địa điểm và tải dữ liệu thời tiết..."):
        # Bước 1: AI nhận diện địa điểm
        location = extract_location_from_prompt(user_question)

        # Bước 2: Lấy dữ liệu API thời tiết thực tế
        weather_data, err = get_weather_forecast(location)

        if err:
            st.error(f"❌ {err}")
        else:
            df = weather_data["df"]
            location_display = weather_data["name"]

            st.success(f"📍 Đã cập nhật dữ liệu thời tiết cho: **{location_display}**")

            # Bố cục 2 cột: Bảng dữ liệu & Biểu đồ
            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("1. Dữ liệu dự báo chi tiết (5 ngày):")
                st.dataframe(df, use_container_width=True, height=350)

            with col2:
                st.subheader("2. Biểu đồ Nhiệt độ & Lượng mưa:")
                fig = px.line(
                    df,
                    x="Thời gian",
                    y=["Nhiệt độ (°C)", "Lượng mưa (mm)"],
                    title=f"Xu hướng Thời tiết tại {location_display}",
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)
            st.subheader("3. AI Phân tích & Đưa ra nhận xét:")
            with st.spinner("AI đang tổng hợp báo cáo thời tiết..."):
                analysis = generate_weather_analysis(user_question, location_display, df)
                st.markdown(analysis)