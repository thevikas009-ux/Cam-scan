import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from google.oauth2 import service_account
from datetime import datetime
import io
import re

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Electronics Devices Worldwide",
    layout="centered"
)

# ================= SESSION =================
if "page" not in st.session_state:
    st.session_state.page = "main"

# ================= HEADER (LOGO + COMPANY NAME) =================
def header():
    col1, col2 = st.columns([2, 6])
    with col1:
        st.image("logo.png", width=220)   # logo.png must be in repo root
    with col2:
        st.markdown(
            """
            <h2 style="margin-bottom:0;">
                ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
            </h2>
            <p style="color:gray;margin-top:4px;">
                Smart Visiting Card OCR (Free AI-like)
            </p>
            """,
            unsafe_allow_html=True
        )
    st.divider()

# 🔥 IMPORTANT: CALL HEADER HERE
header()

st.title("📸 Visiting Card OCR to Google Sheet")

# ================= OCR LOAD =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(["en"], gpu=False)

reader = load_reader()

def clean_text(text):
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def run_ocr(image):
    img = np.array(image.convert("RGB"))
    result = reader.readtext(img, detail=0, paragraph=True)
    text = "\n".join(result)
    return clean_text(text)

# ================= GOOGLE SHEET AUTH =================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1

# ================= IMAGE INPUT =================
option = st.radio(
    "Choose image source",
    ["Upload Image", "Open Camera"],
    horizontal=True
)

image = None
file_name = ""

if option == "Upload Image":
    uploaded = st.file_uploader(
        "Upload image",
        type=["jpg", "jpeg", "png"]
    )
    if uploaded:
        image = Image.open(io.BytesIO(uploaded.read()))
        file_name = uploaded.name

elif option == "Open Camera":
    cam = st.camera_input("Click to capture")
    if cam:
        image = Image.open(io.BytesIO(cam.read()))
        file_name = "camera_image"

# ================= PROCESS =================
if image:
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Reading visiting card..."):
        text = run_ocr(image)

    st.subheader("Extracted Text")
    st.text_area("OCR Output", text, height=220)

    if st.button("✅ Save to Google Sheet"):
        try:
            sheet.append_row([
                text,
                file_name,
                str(datetime.now())
            ])

            st.success("🎉 Business card uploaded successfully")

            # RESET PAGE AFTER SUBMIT
            st.session_state.clear()
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to save: {e}")
