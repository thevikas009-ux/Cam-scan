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
        Smart Visiting Card OCR • Any Angle Scanner
        </p>
        """,
        unsafe_allow_html=True
    )

st.divider()
st.subheader("📸 Visiting Card → Google Sheet")

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
    img = image.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    max_size = 1200
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        img = img.resize((int(img.size[0]*ratio), int(img.size[1]*ratio)))
    return img

def ocr_multi_angle(image):
    best_text = ""
    for angle in [0, 90, 180, 270]:
        rotated = image.rotate(angle, expand=True)
        processed = enhance_image(rotated)
        arr = np.array(processed.convert("RGB"))
        result = reader.readtext(arr, detail=0, paragraph=True)
        text = "\n".join(result)
        if len(text) > len(best_text):
            best_text = text
    return best_text

# ---------------- PARSING FUNCTIONS ----------------
def extract_company(text):
    for line in text.split("\n"):
        if line.isupper() and len(line) > 4 and not re.search(r'\d', line):
            return line.strip()
    return ""

def extract_phones(text):
    phones = re.findall(r'\+?\d[\d\s\-]{8,14}\d', text)
    clean = list(set(p.replace(" ", "").replace("-", "") for p in phones))
    return ", ".join(clean)

def extract_emails(text):
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return ", ".join(list(set(emails)))

def extract_websites(text):
    sites = re.findall(r'(https?://\S+|www\.\S+)', text, re.IGNORECASE)
    clean = []
    for s in sites:
        s = s.strip(" ,)")
        if not s.startswith("http"):
            s = "https://" + s
        clean.append(s)
    return ", ".join(list(set(clean)))

def extract_name(text, company):
    for line in text.split("\n"):
        if (
            line != company
            and len(line.split()) <= 4
            and not re.search(r'\d|@|www|http', line, re.IGNORECASE)
        ):
            return line.strip()
    return ""

def extract_designation(text):
    keywords = [
        "manager", "director", "engineer", "officer",
        "founder", "ceo", "cto", "sales", "marketing"
    ]
    for line in text.split("\n"):
        if any(k in line.lower() for k in keywords):
            return line.strip()
    return ""

def extract_address(text):
    lines = []
    for line in text.split("\n"):
        if any(word in line.lower() for word in ["road", "street", "lane", "sector", "block", "city", "state", "india", "pvt", "ltd"]):
            lines.append(line.strip())
    return ", ".join(lines)

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

# ---------------- SESSION STATE ----------------
if "image" not in st.session_state:
    st.session_state.image = None
if "file_name" not in st.session_state:
    st.session_state.file_name = ""

# ---------------- IMAGE SOURCE ----------------
option = st.radio(
    "Choose Image Source",
    ["Upload Image", "Open Camera"],
    horizontal=True
)

if option == "Upload Image":
    uploaded = st.file_uploader("Upload visiting card image", type=["jpg", "png", "jpeg"])
    if uploaded:
        st.session_state.image = Image.open(uploaded)
        st.session_state.file_name = uploaded.name

if option == "Open Camera":
    cam = st.camera_input("Click & capture card")
    if cam:
        st.session_state.image = Image.open(cam)
        st.session_state.file_name = "camera_image"

# ---------------- PROCESS ----------------
if st.session_state.image is not None:

    image = fix_orientation(st.session_state.image)
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Scanning visiting card..."):
        text = ocr_multi_angle(image)

    st.text_area("OCR Raw Output", text, height=260)

    company = extract_company(text)
    phones = extract_phones(text)
    emails = extract_emails(text)
    websites = extract_websites(text)
    name = extract_name(text, company)
    designation = extract_designation(text)
    address = extract_address(text)

    if st.button("✅ Submit"):
        try:
            sheet.append_row([
                text,
                st.session_state.file_name,
                str(datetime.now()),
                company,
                phones,
                emails,
                name,
                designation,
                address,
                websites
            ])

            st.success("✅ Saved successfully")

            # 🔄 RESET STATE
            st.session_state.image = None
            st.session_state.file_name = ""

            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to save: {e}")
