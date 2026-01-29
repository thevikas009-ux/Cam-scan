import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import io, re

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="Electronics Devices Worldwide",
    layout="centered"
)

# ================= HEADER =================
LOGO_URL = "https://drive.google.com/uc?export=view&id=1xq5ehfCCw8Ncv5FxS845Oxh0eAjxR5-I"

st.markdown(
    f"""
    <div style="background:#0f172a;padding:15px;border-radius:12px;
                display:flex;align-items:center;gap:15px;justify-content:center;">
        <img src="{LOGO_URL}" width="55"/>
        <div style="color:white;">
            <div style="font-size:18px;font-weight:700;">
                ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
            </div>
            <div style="font-size:12px;opacity:0.8;">
                Visiting Card OCR • Mobile Safe
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<br>", unsafe_allow_html=True)
st.title("📸 Visiting Card OCR to Google Sheet")

# ================= OCR LOAD =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(["en"], gpu=False)

reader = load_reader()

# ================= IMAGE HELPERS =================
def resize_image(image, max_width=1200):
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)))
    return image

def clean_text(text):
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def run_ocr(image):
    img = np.array(image.convert("RGB"))
    result = reader.readtext(img, detail=0, paragraph=True)
    return clean_text("\n".join(result))

# ================= AI EXTRACTION =================
def extract_phone(text):
    phones = re.findall(r'(\+?\d[\d\s\-]{8,}\d)', text)
    return phones[0] if phones else ""

def extract_email(text):
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return emails[0] if emails else ""

def extract_website(text):
    sites = re.findall(r'(https?://\S+|www\.\S+)', text)
    return sites[0] if sites else ""

def extract_company(text):
    lines = text.split("\n")
    for l in lines:
        if any(x in l.lower() for x in ["pvt", "ltd", "limited", "company", "industries"]):
            return l.strip()
    return lines[0] if lines else ""

def extract_name(text):
    lines = text.split("\n")
    for l in lines:
        if l.istitle() and len(l.split()) <= 3:
            return l.strip()
    return ""

def extract_designation(text):
    keywords = ["manager", "director", "engineer", "sales", "marketing", "ceo"]
    for l in text.split("\n"):
        if any(k in l.lower() for k in keywords):
            return l.strip()
    return ""

def extract_address(text):
    for l in text.split("\n"):
        if any(x in l.lower() for x in ["road", "street", "sector", "area", "india"]):
            return l.strip()
    return ""

# ================= GOOGLE AUTH =================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1
drive_service = build("drive", "v3", credentials=creds)

# ================= IMAGE SOURCE =================
option = st.radio(
    "Choose image source",
    ["Upload Image", "Open Camera"],
    horizontal=True
)

image = None
file_name = ""

if option == "Upload Image":
    uploaded = st.file_uploader(
        "Upload image (max 3MB)",
        type=["jpg", "jpeg", "png"]
    )
    if uploaded:
        if uploaded.size > 3 * 1024 * 1024:
            st.error("❌ Image must be under 3MB")
            st.stop()
        image = resize_image(Image.open(uploaded))
        file_name = uploaded.name

else:
    cam = st.camera_input("Click to capture")
    if cam:
        image = resize_image(Image.open(cam))
        file_name = "camera_image.jpg"

# ================= PROCESS =================
if image:
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Reading visiting card..."):
        text = run_ocr(image)

    st.text_area("OCR Output", text, height=200)

    # AI extraction
    company = extract_company(text)
    phone = extract_phone(text)
    email = extract_email(text)
    name = extract_name(text)
    designation = extract_designation(text)
    address = extract_address(text)
    website = extract_website(text)

    if st.button("✅ Save to Google Sheet"):
        try:
            # Upload image to Drive
            img_bytes = io.BytesIO()
            image.save(img_bytes, format="JPEG")
            img_bytes.seek(0)

            media = MediaIoBaseUpload(img_bytes, mimetype="image/jpeg")
            file = drive_service.files().create(
                body={"name": file_name},
                media_body=media,
                fields="id"
            ).execute()

            drive_link = f"https://drive.google.com/file/d/{file['id']}/view"

            # Append row (A → K)
            sheet.append_row([
                text,                 # A Full OCR
                file_name,            # B Image Name
                str(datetime.now()),  # C Timestamp
                company,              # D Company
                phone,                # E Phone
                email,                # F Email
                name,                 # G Name
                designation,          # H Designation
                address,              # I Address
                website,              # J Website
                drive_link             # K Drive Link
            ])

            st.success("🎉 Card saved successfully")

        except Exception as e:
            st.error(f"❌ Error: {e}")
