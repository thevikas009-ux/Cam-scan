import streamlit as st
import easyocr
import numpy as np
from PIL import Image, ExifTags
import gspread
from google.oauth2 import service_account
from datetime import datetime
import io
import re
import time

# ================= HIDE TRACEBACK =================
st.set_option("client.showErrorDetails", False)

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

# ================= IMAGE FIX =================
def fix_image_orientation(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation]=='Orientation':
                break
        exif = dict(image._getexif().items())
        if exif.get(orientation) == 3:
            image = image.rotate(180, expand=True)
        elif exif.get(orientation) == 6:
            image = image.rotate(270, expand=True)
        elif exif.get(orientation) == 8:
            image = image.rotate(90, expand=True)
    except:
        pass
    return image

def resize_image(image, max_width=1000):
    if image.width > max_width:
        ratio = max_width / image.width
        new_height = int(image.height * ratio)
        image = image.resize((max_width, new_height))
    return image

# ================= OCR =================
@st.cache_resource
def load_reader():
    try:
        return easyocr.Reader(["en"], gpu=False)
    except Exception:
        return None

reader = load_reader()

def run_ocr(image):
    if reader is None:
        return []
    try:
        img = np.array(image.convert("RGB"))
        result = reader.readtext(img, detail=0, paragraph=False)
        return [r.strip() for r in result if len(r.strip()) > 2]
    except Exception:
        return []

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
try:
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1
except Exception:
    sheet = None

# ================= IMAGE UPLOAD ONLY =================
uploaded = st.file_uploader(
    "Upload visiting card image",
    type=["jpg", "jpeg", "png"],
    key=f"upload_{st.session_state.uploader_key}"
)

image = None
file_name = ""

if uploaded:
    try:
        image = Image.open(io.BytesIO(uploaded.read()))
        image = fix_image_orientation(image)
        image = resize_image(image)
        file_name = uploaded.name
    except Exception:
        st.warning("⚠️ Image open nahi ho paayi. Please try another image.")

# ================= PROCESS =================
if image:
    st.image(image, use_column_width=True)

    lines = run_ocr(image)
    if not lines:
        st.warning("⚠️ Text detect nahi hua. Clear image upload karein.")
        st.stop()

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
            if sheet is None:
                st.info("ℹ️ Sheet connection fail. Data save nahi ho paaya.")
            else:
                # ================= AUTOMATIC RETRY =================
                saved = False
                attempts = 0
                max_attempts = 3
                while not saved and attempts < max_attempts:
                    try:
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
                        saved = True
                        st.success("✅ Data saved successfully")
                    except Exception:
                        attempts += 1
                        time.sleep(2)
                if not saved:
                    st.info("ℹ️ Data save nahi ho paaya. Internet ya Sheet check karein.")

    with col2:
        if st.button("🔄 Reset"):
            try:
                st.session_state.uploader_key += 1
                st.rerun()
            except Exception:
                pass
