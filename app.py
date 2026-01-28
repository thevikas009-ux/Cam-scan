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
        Image OCR • Camera Upload System
        </p>
        """,
        unsafe_allow_html=True
    )

st.divider()
st.title("📸 Image to Google Sheet")

# ---------------- OCR LOAD (SAFE) ----------------
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

# ---------------- IMAGE RESIZE (CRITICAL FIX) ----------------
def resize_image(image, max_size=1024):
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.size[0]*ratio), int(image.size[1]*ratio))
        return image.resize(new_size)
    return image

def extract_text(image):
    image = resize_image(image)
    img = np.array(image.convert("RGB"))
    result = reader.readtext(img, detail=0, paragraph=True)
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

# ---------------- SOURCE SELECT ----------------
option = st.radio(
    "Select Image Source",
    ["Upload Image", "Open Camera"],
    horizontal=True
)

image = None
file_name = ""

# ---------------- UPLOAD ----------------
if option == "Upload Image":
    uploaded = st.file_uploader(
        "Upload Image (jpg / png)",
        type=["jpg", "jpeg", "png"]
    )
    if uploaded:
        image = Image.open(uploaded)
        file_name = uploaded.name

# ---------------- CAMERA ----------------
if option == "Open Camera":
    cam = st.camera_input("Tap to open camera")
    if cam:
        image = Image.open(cam)
        file_name = "camera_image"

# ---------------- PROCESS ----------------
if image:
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Reading image..."):
        try:
            text = extract_text(image)
        except Exception as e:
            st.error("❌ Image processing failed. Please use smaller image.")
            st.stop()

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
        except Exception as e:
            st.error("❌ Google Sheet error")
