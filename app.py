import streamlit as st
import easyocr
import numpy as np
from PIL import Image, ImageEnhance, ExifTags
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import time

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Electronics Devices Worldwide",
    layout="centered"
)

# ---------------- HEADER ----------------
col1, col2 = st.columns([2, 6])
with col1:
    st.image("logo.png", width=220)

with col2:
    st.markdown(
        """
        <h2 style="margin-bottom:0;">
        ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
        </h2>
        <p style="color:gray;margin-top:4px;">
        Smart Visiting Card OCR • Mobile Friendly
        </p>
        """,
        unsafe_allow_html=True
    )

st.divider()
st.title("📸 Visiting Card → Google Sheet")

# ---------------- OCR LOAD ----------------
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_reader()

# ---------------- IMAGE HELPERS ----------------
def fix_orientation(img):
    try:
        exif = img._getexif()
        if exif:
            for k, v in ExifTags.TAGS.items():
                if v == "Orientation":
                    o = exif.get(k)
                    if o == 3:
                        img = img.rotate(180, expand=True)
                    elif o == 6:
                        img = img.rotate(270, expand=True)
                    elif o == 8:
                        img = img.rotate(90, expand=True)
    except:
        pass
    return img

def enhance(img):
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.5)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    w, h = img.size
    if max(w, h) < 1200:
        scale = 1200 / max(w, h)
        img = img.resize((int(w*scale), int(h*scale)))

    return img

# ---------------- OCR + CLEANING ----------------
def clean_ocr_text(text):
    lines = text.split("\n")
    out = []

    for l in lines:
        l = l.strip()
        if len(l) < 3:
            continue

        l = re.sub(r'[^A-Za-z0-9@./:+\- ()]', ' ', l)
        l = re.sub(r'\s+', ' ', l)

        alpha_ratio = sum(c.isalpha() for c in l) / max(len(l), 1)
        if alpha_ratio < 0.3:
            continue

        out.append(l)

    return "\n".join(out)

def ocr_any_angle(img):
    best = ""
    for a in [0, 90, 180, 270]:
        r = img.rotate(a, expand=True)
        r = enhance(r)
        arr = np.array(r.convert("RGB"))

        txt = reader.readtext(
            arr,
            detail=0,
            paragraph=True,
            text_threshold=0.7,
            low_text=0.4
        )

        txt = clean_ocr_text("\n".join(txt))
        if len(txt) > len(best):
            best = txt

    return best

# ---------------- DATA EXTRACTORS ----------------
def get_company(t):
    for l in t.split("\n"):
        if l.isupper() and len(l) > 4:
            return l
    return ""

def get_phone(t):
    m = re.search(r'(\+?\d{10,14})', t)
    return m.group(1) if m else ""

def get_email(t):
    m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', t)
    return m.group(0) if m else ""

def get_website(t):
    t = t.replace("WWW.", "www.").replace("Www.", "www.")
    m = re.search(r'(https?://\S+|www\.\S+)', t, re.I)
    if m:
        u = m.group(0)
        if not u.startswith("http"):
            u = "https://" + u
        return u
    return ""

def get_name(t, company):
    for l in t.split("\n"):
        if l != company and not re.search(r'\d|@', l):
            return l
    return ""

def get_designation(t):
    for l in t.split("\n"):
        if any(k in l.lower() for k in ["manager","director","engineer","officer","founder","ceo","sales"]):
            return l
    return ""

def get_address(t):
    addr = []
    for l in t.split("\n"):
        if any(w in l.lower() for w in ["road","street","lane","pvt","ltd","city","state","pin"]):
            addr.append(l)
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

# ---------------- SESSION RESET ----------------
if "reset" not in st.session_state:
    st.session_state.reset = False

# ---------------- IMAGE INPUT ----------------
choice = st.radio("Choose Image Source", ["Upload Image", "Open Camera"], horizontal=True)

image = None
filename = ""

if choice == "Upload Image":
    f = st.file_uploader("Upload visiting card", type=["jpg","jpeg","png"])
    if f:
        image = Image.open(f)
        filename = f.name

if choice == "Open Camera":
    cam = st.camera_input("Tap to open camera")
    if cam:
        image = Image.open(cam)
        filename = "camera_image"

# ---------------- PROCESS ----------------
if image:
    image = fix_orientation(image)
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Scanning card..."):
        text = ocr_any_angle(image)

    st.text_area("OCR Output", text, height=260)

    company = get_company(text)
    phone = get_phone(text)
    email = get_email(text)
    website = get_website(text)
    name = get_name(text, company)
    designation = get_designation(text)
    address = get_address(text)

    if st.button("✅ Submit"):
        sheet.append_row([
            text,
            filename,
            str(datetime.now()),
            company,
            phone,
            email,
            name,
            designation,
            address,
            website
        ])

        st.success("✅ Saved successfully")
        time.sleep(1)
        st.session_state.reset = True
        st.rerun()

# ---------------- RESET PAGE ----------------
if st.session_state.reset:
    st.session_state.reset = False
