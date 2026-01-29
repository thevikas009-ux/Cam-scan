import streamlit as st
import easyocr
import numpy as np
from PIL import Image, ImageEnhance, ExifTags
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import re
import io

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Electronics Devices Worldwide", layout="centered")

# ---------------- SESSION STATE ----------------
if "page" not in st.session_state:
    st.session_state.page = "main"

# ---------------- GOOGLE AUTH ----------------
scope = [
    "https://www.googleapis.com/auth/drive",
    "https://spreadsheets.google.com/feeds",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)

gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key(st.secrets["sheet_id"]).sheet1

drive_service = build("drive", "v3", credentials=creds)

# ---------------- OCR ----------------
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
                    if o == 3: img = img.rotate(180, expand=True)
                    elif o == 6: img = img.rotate(270, expand=True)
                    elif o == 8: img = img.rotate(90, expand=True)
    except:
        pass
    return img

def enhance(img):
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.3)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    return img

def clean_text(text):
    out = []
    for l in text.split("\n"):
        l = re.sub(r'[^A-Za-z0-9@./:+\- ()]', ' ', l)
        l = re.sub(r'\s+', ' ', l).strip()
        if len(l) > 3:
            out.append(l)
    return "\n".join(out)

def ocr_any_angle(img):
    best = ""
    for a in [0, 90, 180, 270]:
        r = enhance(img.rotate(a, expand=True))
        arr = np.array(r.convert("RGB"))
        txt = reader.readtext(arr, detail=0, paragraph=True)
        txt = clean_text("\n".join(txt))
        if len(txt) > len(best):
            best = txt
    return best

# ---------------- DATA EXTRACT ----------------
def find(pattern, text):
    m = re.search(pattern, text, re.I)
    return m.group(0) if m else ""

# ---------------- DRIVE UPLOAD ----------------
def upload_to_drive(image, name):
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    buf.seek(0)

    file_metadata = {"name": name}
    media = MediaIoBaseUpload(buf, mimetype="image/jpeg")

    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    drive_service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"}
    ).execute()

    return f"https://drive.google.com/file/d/{file['id']}/view"

# ================= MAIN PAGE =================
if st.session_state.page == "main":

    col1, col2 = st.columns([2, 6])
    with col1:
        st.image("logo.png", width=220)
    with col2:
        st.markdown(
            "<h2>ELECTRONICS DEVICES WORLDWIDE PVT. LTD.</h2>"
            "<p style='color:gray;'>Visiting Card OCR</p>",
            unsafe_allow_html=True
        )

    st.divider()
    st.title("📸 Upload Business Card")

    source = st.radio("Select Image Source", ["Upload Image", "Open Camera"], horizontal=True)

    image = None
    filename = ""

    if source == "Upload Image":
        f = st.file_uploader("Upload image", type=["jpg","jpeg","png"])
        if f:
            image = Image.open(f)
            filename = f.name

    if source == "Open Camera":
        cam = st.camera_input("Open Camera")
        if cam:
            image = Image.open(cam)
            filename = "camera_image.jpg"

    if image:
        image = fix_orientation(image)
        st.image(image, use_column_width=True)

        with st.spinner("Scanning card..."):
            text = ocr_any_angle(image)

        st.text_area("OCR Output", text, height=220)

        if st.button("✅ Submit"):
            drive_link = upload_to_drive(image, filename)

            sheet.append_row([
                text,
                filename,
                str(datetime.now()),
                find(r'[A-Z ]{4,}', text),
                find(r'\+?\d{10,14}', text),
                find(r'[\w\.-]+@[\w\.-]+\.\w+', text),
                "",
                "",
                "",
                find(r'(https?://\S+|www\.\S+)', text),
                drive_link
            ])

            st.session_state.page = "success"
            st.rerun()

# ================= SUCCESS PAGE =================
if st.session_state.page == "success":
    st.success("🎉 Business Card Uploaded Successfully")
    st.markdown("Your card details & image are safely saved.")

    if st.button("⬅️ Main Menu"):
        st.session_state.page = "main"
        st.rerun()
