import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Image to Google Sheet", layout="centered")
st.title("📸 Image to Google Sheet App")

# ---------------- OCR ----------------
reader = easyocr.Reader(['en'], gpu=False)

def extract_text(image):
    img_array = np.array(image)
    result = reader.readtext(img_array, detail=0)
    return "\n".join(result)   # FULL TEXT AS-IS

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

# ---------------- UPLOAD IMAGE ----------------
if option == "Upload Image":
    uploaded_file = st.file_uploader(
        "Upload image (jpg / png / jpeg)",
        type=["jpg", "png", "jpeg"]
    )
    if uploaded_file:
        image = Image.open(uploaded_file)
        file_name = uploaded_file.name

# ---------------- CAMERA (ONLY WHEN SELECTED) ----------------
if option == "Open Camera":
    camera_image = st.camera_input("Click to open camera")
    if camera_image:
        image = Image.open(camera_image)
        file_name = "camera_image"

# ---------------- PROCESS IMAGE ----------------
if image:
    st.image(image, use_column_width=True)

    text = extract_text(image)

    st.subheader("Extracted Text (Full Raw Data)")
    st.text_area("OCR Output", text, height=250)

    if st.button("Save to Google Sheet"):
        try:
            sheet.append_row([
                text,
                file_name,
                str(datetime.now())
            ])
            st.success("✅ Full OCR data saved to Google Sheet")
        except Exception as e:
            st.error(f"❌ Error: {e}")
