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

# ✅ DRIVE IMPORT
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================= SHOW ERROR =================
st.set_option("client.showErrorDetails", True)

# ================= SESSION STATE =================
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Electronics Devices Worldwide", layout="centered")

# ================= HEADER =================
def header():
    col1, col2 = st.columns([2, 6])
    with col1:
        # Make sure logo.png is in your GitHub repo
        try:
            st.image("logo.png", width=200)
        except:
            st.write("Logo missing")
    with col2:
        st.markdown("""
        <h2 style='margin-bottom:0;'>ELECTRONICS DEVICES WORLDWIDE PVT. LTD.</h2>
        <p style="color:gray;">Visiting Card OCR • Mobile Safe • Address Extraction</p>
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
        image = image.resize((max_width, int(image.height * ratio)))
    return image

# ================= OCR =================
@st.cache_resource
def load_reader():
    try:
        return easyocr.Reader(["en"], gpu=False)
    except:
        return None

reader = load_reader()

def run_ocr(image):
    if reader is None: return []
    try:
        img = np.array(image.convert("RGB"))
        result = reader.readtext(img, detail=0)
        return [r.strip() for r in result if len(r.strip()) > 2]
    except:
        return []

# ================= DATA EXTRACTION =================
def extract_data(lines):
    text = "\n".join(lines)
    
    # Phone, Email, Website Extraction
    phone_matches = re.findall(r"\+?\d[\d\s\-]{8,15}", text)
    phone = phone_matches[0] if phone_matches else ""
    email = ", ".join(set(re.findall(r"\S+@\S+", text)))
    website = ", ".join(set(re.findall(r"(www\.\S+|https?://\S+)", text)))

    name = lines[0] if lines else ""
    company = ""
    designation = ""
    address_lines = []

    # Address keywords to look for
    addr_keywords = ["street", "road", "floor", "building", "plot", "industrial", "area", "nagar", "city", "opp", "near", "sector", "phase"]

    for line in lines:
        low = line.lower()
        if "pvt" in low or "ltd" in low:
            company = line
        if any(word in low for word in ["manager", "director", "engineer", "ceo", "founder"]):
            designation = line
        # Simple Address Logic: Check if line contains address keywords or Pin Code
        if any(word in low for word in addr_keywords) or re.search(r"\b\d{6}\b", line):
            address_lines.append(line)

    address = ", ".join(address_lines)
    return text, company, name, phone, email, designation, address, website

# ================= GOOGLE AUTH =================
try:
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1
except Exception as e:
    st.error(f"❌ Connection Error: {e}")
    sheet = None

# ================= DRIVE UPLOAD =================
def upload_to_drive(image, file_name):
    try:
        service = build("drive", "v3", credentials=creds)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)

        file_metadata = {
            "name": file_name,
            "parents": ["1EVIcT6ewpzYJ_yD2lTahH2Ld-neJj2Ce"] # Check your Folder ID
        }

        media = MediaIoBaseUpload(buffer, mimetype="image/jpeg")
        file = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
        return file.get("webViewLink")
    except Exception as e:
        st.error(f"Upload Error: {e}")
        return ""

# ================= UI =================
uploaded = st.file_uploader("Upload visiting card", type=["jpg","png","jpeg"], key=st.session_state.uploader_key)

if uploaded:
    image = Image.open(uploaded)
    image = fix_image_orientation(image)
    image = resize_image(image)
    st.image(image, width=400)

    lines = run_ocr(image)
    if not lines:
        st.warning("Text detect nahi hua")
    else:
        full_text, company, name, phone, email, designation, address, website = extract_data(lines)

        # Edit fields before saving
        st.subheader("Verify Details")
        col_a, col_b = st.columns(2)
        with col_a:
            v_name = st.text_input("Person Name", value=name)
            v_company = st.text_input("Company", value=company)
            v_phone = st.text_input("Phone/WhatsApp", value=phone)
        with col_b:
            v_email = st.text_input("Email", value=email)
            v_designation = st.text_input("Designation", value=designation)
            v_website = st.text_input("Website", value=website)
        
        v_address = st.text_area("Address", value=address)
        v_remarks = st.text_area("Remarks")

        if st.button("🚀 Save to Google Sheet"):
            with st.spinner("Saving..."):
                file_name = f"{v_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                drive_link = upload_to_drive(image, file_name)
                
                if sheet:
                    # Hyperlink for Sheet
                    clickable_link = f'=HYPERLINK("{drive_link}", "View Card")' if drive_link else "No Link"
                    
                    sheet.append_row([
                        full_text,
                        file_name,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        v_company,
                        v_name,
                        v_phone,
                        v_email,
                        v_designation,
                        v_address,
                        v_website,
                        v_remarks,
                        clickable_link
                    ], value_input_option="USER_ENTERED")

                    st.success("✅ Data saved successfully!")
                    st.balloons()