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

# ================= HEADER =================
def header():
    col1, col2 = st.columns([2, 6])
    with col1:
        st.image("logo.png", width=200)
    with col2:
        st.markdown(
            """
            <h2 style="margin-bottom:0;">
                ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
            </h2>
            <p style="color:gray;margin-top:4px;">
                Visiting Card OCR • Mobile Safe
            </p>
            """,
            unsafe_allow_html=True
        )
    st.divider()

header()
st.title("📸 Visiting Card OCR to Google Sheet")

# ================= OCR LOAD =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(["en"], gpu=False)

reader = load_reader()

# ================= IMAGE SAFE HELPERS =================
def resize_image(image, max_width=1000):
    if image.width > max_width:
        ratio = max_width / image.width
        new_height = int(image.height * ratio)
        image = image.resize((max_width, new_height))
    return image

def clean_text(text):
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def run_ocr(image):
    img = np.array(image.convert("RGB"))
    result = reader.readtext(img, detail=0, paragraph=True)
    return clean_text("\n".join(result))

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

# ================= IMAGE SOURCE =================
option = st.radio(
    "Choose image source",
    ["Upload Image", "Open Camera"],
    horizontal=True
)

image = None
file_name = ""

# ================= UPLOAD =================
if option == "Upload Image":
    uploaded = st.file_uploader(
        "Upload image (max 3MB)",
        type=["jpg", "jpeg", "png"]
    )
    if uploaded:
        if uploaded.size > 3 * 1024 * 1024:
            st.error("❌ Image too large. Please upload under 3MB.")
            st.stop()

        image = Image.open(io.BytesIO(uploaded.read()))
        image = resize_image(image)
        file_name = uploaded.name

# ================= CAMERA =================
elif option == "Open Camera":
    cam = st.camera_input("Click to capture")
    if cam:
        image = Image.open(io.BytesIO(cam.read()))
        image = resize_image(image)
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

            st.info("⬇️ Upload another card using options above")

        except Exception as e:
            st.error(f"❌ Failed to save: {e}")
