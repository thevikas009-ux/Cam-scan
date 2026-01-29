import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from google.oauth2 import service_account
from datetime import datetime
import io
import re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Electronics Devices Worldwide",
    layout="centered"
)

# ---------------- HEADER BAND (LOGO + COMPANY NAME) ----------------
LOGO_URL = "https://drive.google.com/uc?export=view&id=1xq5ehfCCw8Ncv5FxS845Oxh0eAjxR5-I"

st.markdown(
    f"""
    <div style="
        background-color:#0f172a;
        padding:15px;
        border-radius:12px;
        display:flex;
        align-items:center;
        gap:15px;
        justify-content:center;
    ">
        <img src="{LOGO_URL}" width="70"/>
        <div style="color:white;">
            <div style="font-size:18px;font-weight:700;">
                ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
            </div>
            <div style="font-size:12px;opacity:0.8;">
                Smart OCR • Image to Google Sheet
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)
st.title("📸 Visiting Card OCR")

# ---------------- OCR LOAD ----------------
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

# ---------------- GOOGLE SHEET AUTH ----------------
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

# ---------------- IMAGE INPUT ----------------
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

# ---------------- PROCESS ----------------
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

            # RESET PAGE
            st.session_state.clear()
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to save: {e}")
