import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from google.oauth2 import service_account
from datetime import datetime
import io
import re

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Electronics Devices Worldwide",
    layout="centered"
)

# ================= HEADER =================
def header():
    col1, col2 = st.columns([2, 6])
    with col1:
        st.image("logo.png", width=200)
    with col2:
        st.markdown(
            """
            <h2 style="margin-bottom:0;">
                ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
            </h2>
            <p style="color:gray;margin-top:4px;">
                Visiting Card OCR • Mobile Safe • Free AI
            </p>
            """,
            unsafe_allow_html=True
        )
    st.divider()

header()
st.title("📸 Visiting Card OCR to Google Sheet")

# ================= OCR LOAD =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(["en"], gpu=False)

reader = load_reader()

# ================= IMAGE SAFETY =================
def resize_image(image, max_width=1000):
    if image.width > max_width:
        ratio = max_width / image.width
        new_height = int(image.height * ratio)
        image = image.resize((max_width, new_height))
    return image

# ================= TEXT CLEAN =================
def clean_text(text):
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def run_ocr(image):
    img = np.array(image.convert("RGB"))
    result = reader.readtext(img, detail=0, paragraph=True)
    return clean_text("\n".join(result))

# ================= SMART EXTRACTION =================
DESIGNATION_WORDS = [
    "manager", "engineer", "director", "sales",
    "marketing", "executive", "officer", "ceo",
    "cto", "founder", "owner", "lead", "head",
    "consultant", "supervisor", "admin", "partner"
]

def extract_data(text):
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 2]

    phone = ", ".join(set(re.findall(r"\+?\d[\d\s\-]{8,15}", text)))
    email = ", ".join(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
    website = ", ".join(set(re.findall(r"(?:www\.|https?://)[^\s]+", text)))

    company = ""
    name = ""
    designation = ""
    address_lines = []

    for line in lines:
        low = line.lower()

        # Company
        if not company and any(x in low for x in ["pvt", "ltd", "llp", "industries", "company"]):
            company = line
            continue

        # Designation (CASE-INSENSITIVE, CAPS SAFE)
        if not designation:
            for word in DESIGNATION_WORDS:
                if re.search(rf"\b{word}\b", line, re.IGNORECASE):
                    designation = line.strip()
                    break
            if designation:
                continue


        # Name (clean – no number, no email, no website)
        if not name:
            if (
                not re.search(r"\d", line)
                and "@" not in line
                and "www" not in low
                and "http" not in low
                and len(line.split()) <= 4
            ):
                name = line
                continue

        # Address
        if any(x in low for x in ["road", "street", "sector", "block", "india", "pin"]):
            address_lines.append(line)

    address = ", ".join(address_lines)

    return company, phone, email, name, designation, address, website
# ================= GOOGLE SHEET AUTH =================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1

# ================= IMAGE SOURCE =================
option = st.radio(
    "Choose image source",
    ["Upload Image", "Open Camera"],
    horizontal=True
)

image = None
file_name = ""

# ================= UPLOAD =================
if option == "Upload Image":
    uploaded = st.file_uploader(
        "Upload image (max 3MB)",
        type=["jpg", "jpeg", "png"]
    )
    if uploaded:
        if uploaded.size > 3 * 1024 * 1024:
            st.error("❌ Image too large. Please upload under 3MB.")
            st.stop()

        image = Image.open(io.BytesIO(uploaded.read()))
        image = resize_image(image)
        file_name = uploaded.name

# ================= CAMERA =================
elif option == "Open Camera":
    cam = st.camera_input("Click to capture")
    if cam:
        image = Image.open(io.BytesIO(cam.read()))
        image = resize_image(image)
        file_name = "camera_image"

# ================= PROCESS =================
if image:
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Reading visiting card..."):
        full_text = run_ocr(image)

    st.subheader("Extracted Text")
    st.text_area("OCR Output", full_text, height=220)

    company, phone, email, name, designation, address, website = extract_data(full_text)

    if st.button("✅ Save to Google Sheet"):
        try:
            sheet.append_row([
                full_text,                     # A Full OCR Text
                file_name,                     # B Image Name
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # C Timestamp
                company,                       # D Company
                phone,                         # E Phone
                email,                         # F Email
                name,                          # G Name
                designation,                   # H Designation
                address,                       # I Address
                website,                       # J Website
                ""                              # K Drive Link (EMPTY)
            ])

            st.success("🎉 Business card uploaded successfully")
            st.info("⬆️ Upload next card using options above")

        except Exception as e:
            st.error(f"❌ Failed to save: {e}")
