import streamlit as st
import re
import io
from PIL import Image, ImageOps
import pytesseract
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import gspread

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Business Card Scanner", layout="centered")

FOLDER_ID = "1R3HdbUKtV3ny2Twp0x02yvVp7pz6qdT0"

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

# ---------------- IMAGE & OCR ----------------
def preprocess_image(img):
    img = ImageOps.exif_transpose(img)
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    return img

def extract_text(img):
    return pytesseract.image_to_string(img, config="--oem 3 --psm 6")

def clean_text(text):
    lines = []
    for l in text.split("\n"):
        l = l.strip()
        if len(l) > 2:
            lines.append(l)
    return "\n".join(lines)

# ---------------- AI-LIKE EXTRACTION ----------------
def find_email(text):
    m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return m.group(0) if m else ""

def find_all_phones(text):
    phones = re.findall(r"\+?\d[\d\s\-]{8,}\d", text)
    return list(set([p.replace(" ", "").replace("-", "") for p in phones]))

def find_whatsapp(text):
    phones = find_all_phones(text)
    text_lower = text.lower()

    for p in phones:
        if "whatsapp" in text_lower or "wa.me" in text_lower or "wa " in text_lower:
            return p

    return phones[0] if phones else ""

def find_website(text):
    m = re.search(r"(https?:\/\/[^\s]+|www\.[^\s]+)", text, re.I)
    if m:
        url = m.group(0)
        if not url.lower().startswith("http"):
            url = "https://" + url
        return url
    return ""

def extract_name(text):
    blacklist = ["mobile", "phone", "email", "www", "http", "whatsapp"]
    for line in text.split("\n")[:5]:
        if not any(b in line.lower() for b in blacklist):
            if len(line.split()) <= 4 and not re.search(r"\d", line):
                return line.title()
    return ""

def extract_company(text):
    keywords = [
        "pvt", "ltd", "llp", "inc", "electronics", "technologies",
        "solutions", "systems", "industries", "worldwide"
    ]

    for line in text.split("\n"):
        l = line.lower()
        if any(k in l for k in keywords):
            return line.upper()

    return ""

# ---------------- DRIVE ----------------
def upload_to_drive(image, filename):
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    file_metadata = {"name": filename, "parents": [FOLDER_ID]}
    media = MediaIoBaseUpload(buffer, mimetype="image/jpeg")

    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = file["id"]

    drive_service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"}
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"

# ---------------- SHEET ----------------
def save_to_sheet(row):
    sh = gc.open("Business_Card_Data")
    ws = sh.sheet1
    ws.append_row(row)

# ---------------- SESSION ----------------
if "page" not in st.session_state:
    st.session_state.page = "upload"

# ---------------- UI ----------------
if st.session_state.page == "upload":

    st.title("📇 Business Card Scanner")

    uploaded = st.file_uploader(
        "Upload Business Card Image",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded:
        image = Image.open(uploaded)
        st.image(image, use_container_width=True)

        if st.button("✅ Submit"):
            with st.spinner("Processing..."):

                img = preprocess_image(image)
                raw = extract_text(img)
                text = clean_text(raw)

                name = extract_name(text)
                company = extract_company(text)
                email = find_email(text)
                whatsapp = find_whatsapp(text)
                website = find_website(text)

                drive_link = upload_to_drive(
                    image,
                    uploaded.name.replace(" ", "_")
                )

                save_to_sheet([
                    name,
                    company,
                    whatsapp,
                    email,
                    website,
                    drive_link,
                    text
                ])

            st.session_state.page = "success"
            st.rerun()

elif st.session_state.page == "success":

    st.success("🎉 Business Card Uploaded Successfully")

    if st.button("🏠 Main Menu"):
        st.session_state.page = "upload"
        st.rerun()
