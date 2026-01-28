import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import re

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
        Smart OCR • Image to Google Sheet
        </p>
        """,
        unsafe_allow_html=True
    )

st.divider()
st.title("📸 Image OCR & Structured Sheet Upload")

# ---------------- OCR ----------------
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

def extract_text(image):
    img_array = np.array(image.convert("RGB"))
    result = reader.readtext(img_array, detail=0, paragraph=True)
    return "\n".join(result)

# ---------------- PARSING FUNCTIONS ----------------
def extract_company(text):
    lines = text.split("\n")
    for line in lines:
        if len(line.strip()) > 2 and line.isupper():
            return line.strip()
    return ""

def extract_phone(text):
    match = re.search(r'(\+?\d{10,14})', text)
    return match.group(1) if match else ""

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else ""

def extract_name(text, company_name):
    # Name = line before company name OR first line not company/email/phone
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines:
        if line != company_name and not re.search(r'[\d@]', line):
            return line
    return ""

def extract_designation(text):
    lines = text.split("\n")
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ["manager", "director", "ceo", "founder", "engineer", "officer"]):
            return line.strip()
    return ""

def extract_address(text):
    lines = text.split("\n")
    address_lines = []
    for line in lines:
        if any(c.isdigit() for c in line) or any(word in line.lower() for word in ["street", "road", "lane", "pvt", "ltd", "city", "zip", "state"]):
            address_lines.append(line.strip())
    return ", ".join(address_lines) if address_lines else ""

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

    st.subheader("Extracted Full Text")
    st.text_area("OCR Output", text, height=260)

    # ---------------- AUTO PARSE ----------------
    company_name = extract_company(text)
    phone = extract_phone(text)
    email = extract_email(text)
    name = extract_name(text, company_name)
    designation = extract_designation(text)
    address = extract_address(text)

    if st.button("Save to Google Sheet"):
        try:
            sheet.append_row([
                text,            # A: Full OCR
                file_name,       # B: File Name
                str(datetime.now()),  # C: Timestamp
                company_name,    # D: Company Name
                phone,           # E: Phone Number
                email,           # F: Email
                name,            # G: Name
                designation,     # H: Designation
                address          # I: Address
            ])
            st.success("✅ Saved successfully")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error saving: {e}")
