import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from google.oauth2 import service_account
from datetime import datetime
import io
import re

# ================= SESSION STATE INIT =================
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

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
def extract_data(text):
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 2]

    phone = ", ".join(set(re.findall(r"\+?\d[\d\s\-]{8,15}", text)))
    whatsapp = phone
    email = ", ".join(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
    website = ", ".join(set(re.findall(r"(?:www\.|https?://)[^\s]+", text)))

    company = ""
    name = ""
    designation = ""
    address_lines = []

    for line in lines:
        low = line.lower()

        if not company and re.search(r"\b(pvt|private|ltd|limited|llp|company|corp|industries|services)\b", low):
            company = line
            continue

        if not designation and re.search(
            r"\b(manager|engineer|director|owner|partner|founder|ceo|executive|officer)\b", low
        ):
            designation = line
            continue

        if not name and not re.search(r"\d|@|www|http", low) and len(line.split()) <= 4:
            name = line
            continue

        if any(x in low for x in ["road", "street", "sector", "block", "india", "pin", "plot", "building"]):
            address_lines.append(line)

    address = ", ".join(address_lines)
    return company, phone, whatsapp, email, name, designation, address, website

# ================= GOOGLE SHEET AUTH =================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

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
    horizontal=True,
    key=f"source_{st.session_state.uploader_key}"
)

image = None
file_name = ""

# ================= UPLOAD =================
if option == "Upload Image":
    uploaded = st.file_uploader(
        "Upload image (max 3MB)",
        type=["jpg", "jpeg", "png"],
        key=f"upload_{st.session_state.uploader_key}"
    )
    if uploaded:
        image = Image.open(io.BytesIO(uploaded.read()))
        image = resize_image(image)
        file_name = uploaded.name

# ================= CAMERA =================
elif option == "Open Camera":
    cam = st.camera_input(
        "Click to capture",
        key=f"camera_{st.session_state.uploader_key}"
    )
    if cam:
        image = Image.open(io.BytesIO(cam.read()))
        image = resize_image(image)
        file_name = "camera_image"

# ================= PROCESS =================
if image:
    st.image(image, use_column_width=True)

    full_text = run_ocr(image)

    st.subheader("Extracted Text")
    st.text_area(
        "OCR Output",
        full_text,
        height=220,
        key=f"ocr_{st.session_state.uploader_key}"
    )

    company, phone, whatsapp, email, name, designation, address, website = extract_data(full_text)

    st.text_input(
        "Phone Number",
        whatsapp,
        key=f"whatsapp_{st.session_state.uploader_key}"
    )

    # ================= CHECKBOX =================
    st.subheader("Inspection Options")

    seal_integrity = st.checkbox("Seal Integrity", key=f"seal_{st.session_state.uploader_key}")
    robotics = st.checkbox("Robotics", key=f"robotics_{st.session_state.uploader_key}")
    cap_clouser = st.checkbox("Cap and Clouser", key=f"cap_{st.session_state.uploader_key}")

    selected_options = []
    if seal_integrity:
        selected_options.append("Seal Integrity")
    if robotics:
        selected_options.append("Robotics")
    if cap_clouser:
        selected_options.append("Cap and Clouser")

    selected_options_str = ", ".join(selected_options)

    remarks = st.text_area(
        "Enter remarks",
        height=120,
        key=f"remarks_{st.session_state.uploader_key}"
    )

    # ================= SAVE + RESET =================
    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Save to Google Sheet"):
            sheet.append_row([
                full_text,
                file_name,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                company,
                phone,
                whatsapp,
                email,
                name,
                designation,
                address,
                website,
                selected_options_str,
                remarks,
                ""
            ])
            st.success("🎉 Data saved successfully")

    with col2:
        if st.button("🔄 Reset Page"):
            st.session_state.uploader_key += 1
            st.rerun()
