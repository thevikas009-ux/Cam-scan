import streamlit as st
import pytesseract
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io

st.set_page_config(page_title="Image to Google Sheet", layout="centered")
st.title("📸 Image to Google Sheet App")

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)
client = gspread.authorize(creds)

sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1

uploaded_file = st.file_uploader(
    "Upload image (jpg / png / jpeg)",
    type=["jpg", "png", "jpeg"]
)

if uploaded_file:
    image = Image.open(io.BytesIO(uploaded_file.read()))
    st.image(image, use_column_width=True)

    text = pytesseract.image_to_string(image)

    st.subheader("Extracted Text")
    st.text_area("OCR Output", text, height=200)

    if st.button("Save to Google Sheet"):
        sheet.append_row([
            text,
            uploaded_file.name,
            str(datetime.now())
        ])
        st.success("✅ Data saved to Google Sheet")
