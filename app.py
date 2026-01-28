import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Electronics Devices Worldwide",
    layout="centered"
)

# ---------------- HEADER (BIG LOGO + COMPANY NAME) ----------------
st.markdown(
    """
    <style>
    .header-container {
        display: flex;
        align-items: center;
        gap: 20px;
        margin-bottom: 10px;
    }
    .company-name {
        font-size: 28px;
        font-weight: 700;
        line-height: 1.2;
    }
    .tagline {
        color: gray;
        font-size: 14px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2 = st.columns([2, 5])

with col1:
    st.image("logo.png", width=160)  # 🔥 LOGO SIZE INCREASED

with col2:
    st.markdown(
        """
        <div class="header-container">
            <div>
                <div class="company-name">
                    ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
                </div>
                <div class="tagline">
                    Smart OCR • Image Upload System
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# ---------------- APP TITLE ----------------
st.title("📸 Image to Google Sheet (OCR)")

# ---------------- OCR LOAD ----------------
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

def extract_text(image):
    img_array = np.array(image.convert("RGB"))
    result = reader.readtext(img_array, detail=0, paragraph=True)
    return "\n".join(result)

# ---------------- GOOGLE SHEET AUTH ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1

# ---------------- IMAGE SOURCE ----------------
option = st.radio(
    "Choose image source",
    ["Upload Image", "Open Camera"],
    horizontal=True
)

image = None
file_name = ""

# ---------------- FILE UPLOAD ----------------
if option == "Upload Image":
    uploaded_file = st.file_uploader(
        "Upload image (jpg / png / jpeg)",
        type=["jpg", "png", "jpeg"]
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        file_name = uploaded_file.name

# ---------------- CAMERA ----------------
if option == "Open Camera":
    cam = st.camera_input("Click button to open camera")
    if cam:
        image = Image.open(cam)
        file_name = "camera_image"

# ---------------- PROCESS ----------------
if image:
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Scanning image..."):
        text = extract_text(image)

    st.subheader("Extracted Full Text")
    st.text_area("OCR Result", text, height=260)

    if st.button("Save to Google Sheet"):
        try:
            sheet.append_row([
                text,
                file_name,
                str(datetime.now())
            ])
            st.success("✅ Data saved successfully")
        except Exception as e:
            st.error(f"❌ Error: {e}")
