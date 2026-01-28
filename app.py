import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Electronics Devices Worldwide",
    layout="centered"
)

# ---------------- HEADER ----------------
col1, col2 = st.columns([2, 5])

with col1:
    st.image("logo.png", width=180)

with col2:
    st.markdown(
        """
        <h2 style="margin-bottom:0;">
        ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
        </h2>
        <p style="color:gray;margin-top:4px;">
        Image to Google Sheet OCR System
        </p>
        """,
        unsafe_allow_html=True
    )

st.divider()

st.title("📸 Image to Google Sheet")

# ---------------- OCR ----------------
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

def extract_text(image):
    img_array = np.array(image.convert("RGB"))
    result = reader.readtext(img_array, detail=0, paragraph=True)
    return "\n".join(result)

# ---------------- GOOGLE SHEET ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"],
    scope
)

client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1

# ---------------- IMAGE SOURCE ----------------
option = st.radio(
    "Choose Image Source",
    ["Upload Image", "Open Camera"],
    horizontal=True
)

image = None
file_name = ""

# ---------------- UPLOAD IMAGE ----------------
if option == "Upload Image":
    uploaded_file = st.file_uploader(
        "Upload image",
        type=["jpg", "png", "jpeg"]
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        file_name = uploaded_file.name

# ---------------- CAMERA ----------------
if option == "Open Camera":
    cam = st.camera_input("Click to open camera")
    if cam:
        image = Image.open(cam)
        file_name = "camera_image"

# ---------------- PROCESS ----------------
if image:
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Scanning image..."):
        text = extract_text(image)

    st.subheader("Extracted Text")
    st.text_area("OCR Output", text, height=250)

    if st.button("Save to Google Sheet"):
        try:
            sheet.append_row([
                text,
                file_name,
                str(datetime.now())
            ])

            st.success("✅ Saved successfully")
            time.sleep(2)
            st.rerun()

        except Exception:
            st.error("❌ Error saving to Google Sheet")
