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

# ---------------- OCR READER ----------------
reader = easyocr.Reader(['en'], gpu=False)

def extract_text(image):
    img_array = np.array(image)
    result = reader.readtext(img_array, detail=0)
    return " ".join(result)

# ---------------- GOOGLE SHEET AUTH ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Make sure your secrets.toml has gcp_service_account as a dictionary
# and sheet_id as just the Sheet ID (not full URL)
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open your Google Sheet
sheet = client.open_by_key(st.secrets["sheet_id"]).Sheet1

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader(
    "Upload image (jpg / png / jpeg)",
    type=["jpg", "png", "jpeg"]
)

if uploaded_file:
    image = Image.open(io.BytesIO(uploaded_file.read()))
    st.image(image, use_column_width=True)

    # ✅ OCR
    text = extract_text(image)

    st.subheader("Extracted Text")
    st.text_area("OCR Output", text, height=200)

    if st.button("Save to Google Sheet"):
        try:
            sheet.append_row([
                text,
                uploaded_file.name,
                str(datetime.now())
            ])
            st.success("✅ Data saved to Google Sheet")
        except Exception as e:
            st.error(f"Error saving to Sheet: {e}")

# ---------------- DEBUG: Check Secrets ----------------
# Uncomment this temporarily to make sure Streamlit sees your secrets
# st.write(st.secrets)
