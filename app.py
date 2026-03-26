import streamlit as st
import easyocr
import numpy as np
from PIL import Image, ExifTags
import gspread
from google.oauth2 import service_account
from datetime import datetime
import io
import re

# ✅ DRIVE IMPORT
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Electronics Devices Worldwide", layout="centered")

# ================= HEADER =================
def header():
    col1, col2 = st.columns([2, 6])
    with col1:
        try:
            st.image("logo.png", width=200)
        except:
            st.write("Logo missing")
    with col2:
        st.markdown("""
        <h2 style='margin-bottom:0;'>ELECTRONICS DEVICES WORLDWIDE PVT. LTD.</h2>
        <p style="color:gray;">Visiting Card OCR • Official Database System</p>
        """, unsafe_allow_html=True)
    st.divider()

header()

# ================= IMAGE PROCESSING =================
def fix_image_orientation(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation]=='Orientation':
                break
        exif = dict(image._getexif().items())
        if exif.get(orientation) == 3: image = image.rotate(180, expand=True)
        elif exif.get(orientation) == 6: image = image.rotate(270, expand=True)
        elif exif.get(orientation) == 8: image = image.rotate(90, expand=True)
    except: pass
    return image

# ================= OCR & EXTRACTION =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(["en"], gpu=False)

reader = load_reader()

def extract_details(image):
    img = np.array(image.convert("RGB"))
    lines = reader.readtext(img, detail=0)
    
    # 1. Full OCR Text (Column A)
    full_ocr_raw = "\n".join(lines)
    
    # Regex for Phone, Email, Web
    phone = re.findall(r"\+?\d[\d\s\-]{8,15}", full_ocr_raw)
    email = re.findall(r"\S+@\S+", full_ocr_raw)
    web = re.findall(r"(www\.\S+|https?://\S+)", full_ocr_raw)
    
    # Basic logic for Name, Company, Address
    name = lines[0] if lines else ""
    company = ""
    designation = ""
    address_list = []
    
    addr_keys = ["road", "street", "floor", "building", "plot", "industrial", "area", "nagar", "city", "opp", "near", "sector", "phase"]

    for line in lines:
        low = line.lower()
        if "pvt" in low or "ltd" in low: company = line
        if any(w in low for w in ["manager", "director", "engineer", "ceo"]): designation = line
        if any(w in low for w in addr_keys) or re.search(r"\b\d{6}\b", line): address_list.append(line)

    return {
        "full_text": full_ocr_raw,
        "company": company,
        "name": name,
        "phone": phone[0] if phone else "",
        "email": email[0] if email else "",
        "designation": designation,
        "address": ", ".join(address_list),
        "website": web[0] if web else ""
    }

# ================= DRIVE UPLOAD =================
def upload_to_drive(image, file_name):
    try:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=creds)
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)
        meta = {"name": file_name, "parents": ["1EVIcT6ewpzYJ_yD2lTahH2Ld-neJj2Ce"]}
        media = MediaIoBaseUpload(buf, mimetype="image/jpeg")
        file = service.files().create(body=meta, media_body=media, fields="webViewLink").execute()
        return file.get("webViewLink")
    except Exception as e:
        st.error(f"Drive Error: {e}")
        return ""

# ================= MAIN UI =================
uploaded = st.file_uploader("Upload visiting card", type=["jpg","png","jpeg"])

if uploaded:
    img = Image.open(uploaded)
    img = fix_image_orientation(img)
    st.image(img, width=350)

    with st.spinner("Scanning Card..."):
        data = extract_details(img)

    st.subheader("📝 Verify & Edit Details")
    col1, col2 = st.columns(2)
    v_name = col1.text_input("Person Name", value=data["name"])
    v_comp = col2.text_input("Company Name", value=data["company"])
    v_phone = col1.text_input("Phone Number", value=data["phone"])
    v_email = col2.text_input("Email ID", value=data["email"])
    v_desig = col1.text_input("Designation", value=data["designation"])
    v_web = col2.text_input("Website", value=data["website"])
    v_addr = st.text_area("Office Address", value=data["address"])

    st.subheader("⚙️ Inspection Options")
    c1, c2 = st.columns(2)
    opt1 = c1.checkbox("Seal Integrity")
    opt2 = c1.checkbox("Robotics")
    opt3 = c2.checkbox("Cap and Clouser")
    opt4 = c2.checkbox("Induction Capsealing")
    
    selected_opts = ", ".join([opt for opt, val in zip(["Seal Integrity", "Robotics", "Cap and Clouser", "Induction Capsealing"], [opt1, opt2, opt3, opt4]) if val])
    
    v_remarks = st.text_area("Remarks")

    if st.button("🚀 Save Everything"):
        with st.spinner("Saving to Cloud..."):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_name = f"{v_name}_{datetime.now().strftime('%H%M%S')}.jpg"
            
            drive_link = upload_to_drive(img, file_name)
            
            try:
                creds = service_account.Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"],
                    scopes=["https://www.googleapis.com/auth/spreadsheets"]
                )
                client = gspread.authorize(creds)
                sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1
                
                # --- PERFECT COLUMN SEQUENCE (A to M) ---
                row_to_save = [
                    data["full_text"],   # A: Full OCR Text
                    file_name,           # B: File Name
                    timestamp,           # C: Timestamp
                    v_comp,              # D: Company Name
                    v_name,              # E: Person Name
                    v_phone,             # F: Phone Number
                    v_email,             # G: Email ID
                    v_desig,             # H: Designation
                    v_addr,              # I: Office Address
                    v_web,               # J: Website
                    selected_opts,       # K: Inspection Options
                    v_remarks,           # L: Remarks
                    f'=HYPERLINK("{drive_link}", "View Card")' # M: Drive Photo Link
                ]
                
                sheet.append_row(row_to_save, value_input_option="USER_ENTERED")
                st.success("✅ Data saved in all columns A to M!")
                st.balloons()
            except Exception as e:
                st.error(f"Sheet Error: {e}")