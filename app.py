import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="BUSINESS CARD UPLOAD", layout="centered")

# ---------------- HEADER (LOGO + COMPANY NAME) ----------------
LOGO_URL = "https://drive.google.com/uc?export=view&id=1xq5ehfCCw8Ncv5FxS845Oxh0eAjxR5-I"

col1, col2 = st.columns([1, 4])

with col1:
    st.image(LOGO_URL, width=80)

with col2:
    st.markdown(
        """
        <div style="padding-top:8px">
            <h3 style="margin-bottom:0;">
                ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
            </h3>
            <p style="margin-top:2px;color:gray;">
                Smart OCR • Image to Google Sheet
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

st.title("📸 Image to Google Sheet App")

# ---------------- OCR (CACHED FOR MOBILE) ----------------
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

# ---------------- IMAGE SOURCE OPTION ----------------
option = st.radio(
    "Choose image source",
    ["Upload Image", "Open Camera"],
    horizontal=True
)

image = None
file_name = ""
uploaded_file = None

# ---------------- UPLOAD IMAGE ----------------
if option == "Upload Image":
    uploaded_file = st.file_uploader(
        "Upload image (jpg / png / jpeg)",
        type=["jpg", "png", "jpeg"]
    )

    if uploaded_file:
        if uploaded_file.size > 4 * 1024 * 1024:
            st.error("❌ Image too large. Please upload image under 4MB")
            st.stop()

        image = Image.open(uploaded_file)
        file_name = uploaded_file.name

# ---------------- CAMERA (CLICK TO OPEN) ----------------
if option == "Open Camera":
    camera_image = st.camera_input("Click to open camera")
    if camera_image:
        image = Image.open(camera_image)
        file_name = "camera_image"

# ---------------- PROCESS IMAGE ----------------
if image:
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Scanning image, please wait..."):
        text = extract_text(image)

    st.subheader("Extracted Text (Full Raw Data)")
    st.text_area("OCR Output", text, height=260)

    if st.button("Save to Google Sheet"):
        try:
            sheet.append_row([
                text,
                file_name,
                str(datetime.now())
            ])
            st.success("✅ Data saved to Google Sheet")
        except Exception as e:
            st.error(f"❌ Error saving data: {e}")
