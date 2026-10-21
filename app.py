import os
from datetime import datetime, timezone, timedelta
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Cấu hình trang
st.set_page_config(page_title="WeatherAI Intelligence PRO", page_icon="⚡", layout="wide")

# Ẩn các thành phần dư thừa của Streamlit để nhường chỗ cho giao diện Custom HTML
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding: 0rem !important; max-width: 100% !important;}
    </style>
""", unsafe_allow_html=True)

# Đọc file HTML thiết kế gốc
HTML_FILE_PATH = "extracted_design/code.html"  # Đường dẫn tới file code.html trong project của bạn

if os.path.exists(HTML_FILE_PATH):
    with open(HTML_FILE_PATH, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Hiển thị trọn vẹn giao diện HTML/Tailwind CSS chuẩn mẫu
    components.html(html_content, height=1400, scrolling=True)
else:
    st.error("❌ Không tìm thấy file `code.html`. Vui lòng kiểm tra lại đường dẫn thư mục!")
