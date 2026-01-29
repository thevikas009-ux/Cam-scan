import streamlit as st
import easyocr
import numpy as np
from PIL import Image, ImageOps
import re
import io
from datetime import datetime
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Business Card Scanner", layout="centered")

DRIVE_FOLDER_ID = "1R3HdbUKtV3ny2Twp0x02yvVp7pz6qdT0"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

# ---------------- AUTH ----------------
creds = service_account.Credentials.from_service_account_file(
    "service_account.json", scopes=SCOPES
)

drive_service = build("drive", "v3", credentials=creds)
gc = gspread.authorize(creds)

# ---------------- OCR ----------------
@st.cache_resource
def load_reader():
    return easyocr.Reader(["en"], gpu=False)

reader = load_reader()

def preprocess(img):
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    return img

def run_ocr(img):
    result = reader.readtext(np.array(img), detail=0, paragraph=True)
    return "\n".join(result)

# ---------------- AI CLEANING ----------------
def clean_text(text):
    lines = []
    for l in text.split("\n"):
        l = l.strip()
        if len(l) > 2:
            lines.append(l)
    return "\n".join(lines)

def extract_email(text):
    m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return m.group(0) if m else ""

def extract_phones(text):
    return re.findall(r"\+?\d[\d\s\-]{8,}\d", text)

def extract_whatsapp(text):
    phones = extract_phones(text)
    return phones[0].replace(" ", "").replace("-", "") if phones else ""

def extract_website(text):
    m = re.search(r"(https?:\/\/\S+|www\.\S+)", text, re.I)
    if m:
        url = m.group(0)
        if not url.startswith("http"):
            url = "https://" + url
        return url
    return ""

def extract_name(text):
    blacklist = ["mobile", "phone", "email", "www", "http", "whatsapp"]
    for line in text.split("\n")[:6]:
        if not any(b in line.lower() for b in blacklist):
            if len(line.split()) <= 4 and not re.search(r"\d", line):
                return line.title()
    return ""

def extract_company(text):
    keys = ["pvt", "ltd", "llp", "electronics", "technology", "solutions", "worldwide"]
    for line in text.split("\n"):
        if any(k in line.lower() for k in keys):
            return line.upper()
    return ""

# ---------------- DRIVE UPLOAD ----------------
def upload_drive(image, name):
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    buf.seek(0)

    meta = {"name": name, "parents": [DRIVE_FOLDER_ID]}
    media = MediaIoBaseUpload(buf, mimetype="image/jpeg")

    file = drive_service.files().create(
        body=meta, media_body=media, fields="id"
    ).execute()

    drive_service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()

    return f"https://drive.google.com/file/d/{file['id']}/view"

# ---------------- SHEET ----------------
def save_sheet(row):
    sh = gc.open("Business_Card_Data")
    ws = sh.sheet1
    ws.append_row(row)

# ---------------- SESSION ----------------
if "page" not in st.session_state:
    st.session_state.page = "upload"

# ---------------- UI ----------------
if st.session_state.page == "upload":

    st.title("📇 Business Card Scanner")

    file = st.file_uploader("Upload Card Image", type=["jpg", "png", "jpeg"])

    if file:
        image = Image.open(file)
        st.image(image, use_container_width=True)

        if st.button("✅ Submit"):
            with st.spinner("Processing card..."):
                img = preprocess(image)
                text = clean_text(run_ocr(img))

                name = extract_name(text)
                company = extract_company(text)
                whatsapp = extract_whatsapp(text)
                email = extract_email(text)
                website = extract_website(text)

                drive_link = upload_drive(image, file.name)

                save_sheet([
                    name,
                    company,
                    whatsapp,
                    email,
                    website,
                    drive_link,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    text
                ])

            st.session_state.page = "success"
            st.rerun()

elif st.session_state.page == "success":

    st.success("🎉 Business Card Uploaded Successfully")

    if st.button("🏠 Main Menu"):
        st.session_state.page = "upload"
        st.rerun()
