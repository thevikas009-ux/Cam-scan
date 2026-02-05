import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from google.oauth2 import service_account
from datetime import datetime
import io
import re

# ================= SESSION STATE =================
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Electronics Devices Worldwide", layout="centered")

# ================= HEADER =================
def header():
    col1, col2 = st.columns([2, 6])
    with col1:
        st.image("logo.png", width=200)
    with col2:
        st.markdown("""
        <h2 style="margin-bottom:0;">ELECTRONICS DEVICES WORLDWIDE PVT. LTD.</h2>
        <p style="color:gray;margin-top:4px;">Visiting Card OCR • Mobile Safe • Free AI</p>
        """, unsafe_allow_html=True)
    st.divider()

header()
st.title("📸 Visiting Card OCR to Google Sheet")

# ================= OCR =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(["en"], gpu=False)

reader = load_reader()

def run_ocr(image):
    img = np.array(image.convert("RGB"))
    result = reader.readtext(img, detail=0, paragraph=False)
    return [r.strip() for r in result if len(r.strip()) > 2]

# ================= SMART EXTRACTION =================
def extract_data(lines):
    full_text = "\n".join(lines)

    phone_matches = re.findall(r"\+?\d[\d\s\-]{8,15}", full_text)
    phone = phone_matches[0] if phone_matches else ""
    whatsapp = phone

    email = ", ".join(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", full_text)))
    website = ", ".join(set(re.findall(r"(?:www\.|https?://)[^\s]+", full_text)))

    name = ""
    if phone:
        for i, line in enumerate(lines):
            if phone in line and i > 0:
                possible_name = lines[i - 1]
                if not re.search(r"\d|@|www|http", possible_name.lower()):
                    name = possible_name
                break

    company = ""
    designation = ""
    address_lines = []

    for line in lines:
        low = line.lower()

        if not company and re.search(r"\b(pvt|private|ltd|limited|company|corp|industries)\b", low):
            company = line

        if not designation and re.search(r"\b(manager|director|engineer|owner|ceo|founder|executive)\b", low):
            designation = line

        if any(x in low for x in ["road", "street", "sector", "block", "india", "pin", "plot", "building"]):
            address_lines.append(line)

    address = ", ".join(address_lines)

    return full_text, company, name, phone, whatsapp, email, designation, address, website

# ================= GOOGLE SHEET =================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1

# ================= IMAGE UPLOAD ONLY =================
uploaded = st.file_uploader(
    "Upload visiting card image",
    type=["jpg", "jpeg", "png"],
    key=f"upload_{st.session_state.uploader_key}"
)

image = None
file_name = ""

if uploaded:
    image = Image.open(io.BytesIO(uploaded.read()))
    file_name = uploaded.name

# ================= PROCESS =================
if image:
    st.image(image, use_column_width=True)

    lines = run_ocr(image)

    full_text, company, name, phone, whatsapp, email, designation, address, website = extract_data(lines)

    st.subheader("OCR Text")
    st.text_area("Extracted", full_text, height=200)

    st.subheader("Person Details")
    person_name = st.text_input(
        "Person Name (auto detected, editable)",
        value=name,
        key=f"name_{st.session_state.uploader_key}"
    )

    st.text_input("Phone", phone)
    st.text_input("WhatsApp", whatsapp)
    st.text_input("Email", email)

    remarks = st.text_area("Remarks")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Save"):
            sheet.append_row([
                full_text,
                file_name,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                company,
                person_name,
                phone,
                whatsapp,
                email,
                designation,
                address,
                website,
                remarks
            ])
            st.success("Saved successfully")

    with col2:
        if st.button("🔄 Reset"):
            st.session_state.uploader_key += 1
            st.rerun()
