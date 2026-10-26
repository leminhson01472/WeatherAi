#  WeatherAI Pro - Trợ lý Khí tượng AI Đa tầng

Ứng dụng dự báo thời tiết thời gian thực tích hợp trí tuệ nhân tạo GPT-4o, theo dõi dông bão radar trực quan và quản lý hội thoại đa phiên thông minh.

##  Tính năng nổi bật
- **Phân tích Khí tượng AI**: Tích hợp OpenAI GPT-4o phân tích chi tiết nhiệt độ, lượng mưa, độ ẩm theo thời gian thực.
- Nhận diện chính xác tên địa danh cấp Xã/Huyện/Tỉnh (Đà Nẵng, Đồng Nai, Bình Định,...).
##  Công nghệ sử dụng
- **Frontend / Framework**: Streamlit, Plotly, HTML5/CSS3 Custom.
- **AI Core**: OpenAI GPT-4o (APIGiaRe).
- **Meteorology Data**: OpenWeatherMap API, BigDataCloud Reverse Geocoding, Windy Embedded Map.

##  Cài đặt cục bộ (Local Setup)
```bash
git clone [https://github.com/leminhson01472/weatherai.git](https://github.com/leminhson01472/weatherai.git)
cd weatherai
pip install -r requirements.txt
streamlit run app.py
