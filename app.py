import streamlit as st
import easyocr
import numpy as np
from PIL import Image, ImageEnhance, ExifTags
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
        Smart OCR • Any Angle Card Scanner
        </p>
        """,
        unsafe_allow_html=True
    )

st.divider()
st.title("📸 Visiting Card OCR to Google Sheet")

# ---------------- OCR ----------------
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

# ---------------- IMAGE HELPERS ----------------
def fix_orientation(image):
    try:
        exif = image._getexif()
        if exif:
            for tag, value in ExifTags.TAGS.items():
                if value == "Orientation":
                    orientation_key = tag
                    break
            orientation = exif.get(orientation_key)
            if orientation == 3:
                image = image.rotate(180, expand=True)
            elif orientation == 6:
                image = image.rotate(270, expand=True)
            elif orientation == 8:
                image = image.rotate(90, expand=True)
    except Exception:
        pass
    return image

def enhance_image(image):
    # Convert to grayscale
    img = image.convert("L")
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)
    # Resize if too small
    max_size = 1024
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0]*ratio), int(img.size[1]*ratio))
        img = img.resize(new_size)
    return img

def ocr_multi_angle(image):
    best_text = ""
    max_len = 0

    for angle in [0, 90, 180, 270]:
        rotated = image.rotate(angle, expand=True)
        processed = enhance_image(rotated)
        img_array = np.array(processed.convert("RGB"))
        result = reader.readtext(img_array, detail=0, paragraph=True)
        text = "\n".join(result)

        if len(text) > max_len:
            max_len = len(text)
            best_text = text

    return best_text

# ---------------- PARSING FUNCTIONS ----------------
def extract_company(text):
    for line in text.split("\n"):
        if len(line.strip()) > 2 and line.isupper():
            return line.strip()
    return ""

def extract_phone(text):
    match = re.search(r'(\+?\d{10,14})', text)
    return match.group(1) if match else ""

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else ""

def extract_website(text):
    match = re.search(r'(https?://\S+|www\.\S+)', text, re.IGNORECASE)
    return match.group(0) if match else ""

def extract_name(text, company):
    for line in text.split("\n"):
        if line != company and not re.search(r'[\d@]', line):
            return line.strip()
    return ""

def extract_designation(text):
    for line in text.split("\n"):
        if any(k in line.lower() for k in ["manager", "director", "engineer", "officer", "founder", "ceo"]):
            return line.strip()
    return ""

def extract_address(text):
    addr = []
    for line in text.split("\n"):
        if any(c.isdigit() for c in line) or any(word in line.lower() for word in ["street", "road", "lane", "pvt", "ltd", "city", "zip", "state"]):
            addr.append(line.strip())
    return ", ".join(addr)

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

if option == "Upload Image":
    uploaded_file = st.file_uploader("Upload image", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        image = Image.open(uploaded_file)
        file_name = uploaded_file.name

if option == "Open Camera":
    cam = st.camera_input("Click to open camera")
    if cam:
        image = Image.open(cam)
        file_name = "camera_image"

# ---------------- PROCESS ----------------
if image:
    image = fix_orientation(image)
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Reading card (any angle supported)..."):
        text = ocr_multi_angle(image)

    st.subheader("Extracted Text")
    st.text_area("OCR Output", text, height=260)

    company = extract_company(text)
    phone = extract_phone(text)
    email = extract_email(text)
    website = extract_website(text)
    name = extract_name(text, company)
    designation = extract_designation(text)
    address = extract_address(text)

    if st.button("Submit"):
        try:
            sheet.append_row([
                text, file_name, str(datetime.now()),
                company, phone, email, name, designation, address, website
            ])
            st.success("✅ Saved successfully")
            time.sleep(2)
            st.rerun()  # <-- use this in latest Streamlit

        except Exception as e:
            st.error(f"❌ Failed to save: {e}")
