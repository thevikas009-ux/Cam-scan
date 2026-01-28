import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io
import re  # For field extraction

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="📸 OCR to Google Sheet", layout="centered")
st.title("📸 Image / Camera to Google Sheet App")

# ---------------- OCR READER ----------------
reader = easyocr.Reader(['en'], gpu=False)

def extract_text(image):
    img_array = np.array(image)
    result = reader.readtext(img_array, detail=0)
    return " ".join(result)

# ---------------- FIELD EXTRACTION ----------------
def extract_fields(text):
    lines = text.split("\n")
    
    # Initialize empty fields
    company = name = phone = email = designation = address = ""
    
    # Extract phone numbers
    phone_match = re.findall(r'\+?\d[\d\s\-]{7,}\d', text)
    phone = phone_match[0] if phone_match else ""
    
    # Extract emails
    email_match = re.findall(r'\S+@\S+', text)
    email = email_match[0] if email_match else ""
    
    # Heuristic: first line = company, second = name, third = designation
    if len(lines) > 0:
        company = lines[0]
    if len(lines) > 1:
        name = lines[1]
    if len(lines) > 2:
        designation = lines[2]
    if len(lines) > 3:
        address = " ".join(lines[3:])
    
    return company, name, phone, email, designation, address

# ---------------- GOOGLE SHEET AUTH ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1

# ---------------- FILE UPLOAD OR CAMERA ----------------
uploaded_file = st.file_uploader(
    "Upload image (jpg / png / jpeg)",
    type=["jpg", "png", "jpeg"]
)

camera_image = st.camera_input("Or take a picture with your camera")

# Use whichever the user provided
image_file = uploaded_file or camera_image

if image_file:
    image = Image.open(io.BytesIO(image_file.read()))
    st.image(image, use_column_width=True)

    # OCR extraction
    text = extract_text(image)

    st.subheader("Extracted Text")
    st.text_area("OCR Output", text, height=200)

    # ---------------- SAVE TO GOOGLE SHEET ----------------
    if st.button("Save to Google Sheet"):
        try:
            company, name, phone, email, designation, address = extract_fields(text)
            
            # Append data directly, no header required
            sheet.append_row([
                company,
                name,
                phone,
                email,
                designation,
                address,
                image_file.name if uploaded_file else "Camera Capture",
                str(datetime.now())
            ])
            st.success("✅ Data saved to Google Sheet")
        except Exception as e:
            st.error(f"Error saving to Sheet: {e}")
