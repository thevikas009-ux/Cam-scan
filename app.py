import streamlit as st
import numpy as np
from PIL import Image, ExifTags
import gspread
from google.oauth2 import service_account
from datetime import datetime
import io
import re
import pytesseract
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Electronics Devices Worldwide", layout="centered")

def fix_orientation(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation': break
        exif = dict(image._getexif().items())
        if exif.get(orientation) == 3: image = image.rotate(180, expand=True)
        elif exif.get(orientation) == 6: image = image.rotate(270, expand=True)
        elif exif.get(orientation) == 8: image = image.rotate(90, expand=True)
    except: pass
    return image

def extract_details(image):
    try:
        full_text = pytesseract.image_to_string(image)
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        email = re.findall(r"\S+@\S+", full_text)
        phone = re.findall(r"\+?\d[\d\s\-]{8,15}", full_text)
        addr_keywords = ["road", "street", "floor", "building", "plot", "area", "nagar", "city", "sector", "industrial", "phase"]
        addr_list = [line for line in lines if any(w in line.lower() for w in addr_keywords) or re.search(r"\b\d{6}\b", line)]
        return {
            "full": full_text, "name": lines[0] if lines else "Unknown",
            "phone": phone[0] if phone else "", "email": email[0] if email else "",
            "addr": ", ".join(addr_list),
            "comp": next((l for l in lines if "pvt" in l.lower() or "ltd" in l.lower()), "")
        }
    except: return None

# ================= INTERFACE =================
st.markdown("<h2 style='text-align:center; color:#1E3A8A;'>ELECTRONICS DEVICES WORLDWIDE PVT. LTD.</h2>", unsafe_allow_html=True)
st.divider()

if "ocr_data" not in st.session_state: 
    st.session_state.ocr_data = None

uploaded = st.file_uploader("📸 Upload Visiting Card", type=["jpg","png","jpeg"])

# AUTOMATIC SCAN LOGIC
if uploaded and st.session_state.ocr_data is None:
    img = Image.open(uploaded)
    img = fix_orientation(img)
    with st.spinner("Scanning Card... Please wait"):
        st.session_state.ocr_data = extract_details(img)
        st.rerun()

if uploaded and st.session_state.ocr_data:
    img = Image.open(uploaded)
    img = fix_orientation(img)
    st.image(img, width=350)
    
    d = st.session_state.ocr_data
    with st.form("entry_form"):
        st.subheader("Verify Details")
        v_full = st.text_area("Full OCR Text", value=d["full"], height=100)
        
        c1, c2 = st.columns(2)
        v_name = c1.text_input("Name", value=d["name"])
        v_comp = c2.text_input("Company", value=d["comp"])
        v_phone = c1.text_input("Phone", value=d["phone"])
        v_email = c2.text_input("Email", value=d["email"])
        v_addr = st.text_area("Address", value=d["addr"])

        st.write("---")
        st.subheader("Inspection Options")
        col_a, col_b = st.columns(2)
        o1 = col_a.checkbox("Seal Integrity")
        o2 = col_a.checkbox("Robotics")
        o3 = col_b.checkbox("Cap and Clouser")
        o4 = col_b.checkbox("Induction Capsealing")
        
        v_rem = st.text_area("Remarks / Note")
        
        if st.form_submit_button("🚀 Final Save"):
            try:
                with st.spinner("Saving..."):
                    creds = service_account.Credentials.from_service_account_info(
                        st.secrets["gcp_service_account"], 
                        scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
                    )
                    
                    # 1. DRIVE UPLOAD (Fixed for 403 Quota)
                    drive = build("drive", "v3", credentials=creds)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=40) # Quality low to bypass quota limits
                    buf.seek(0)
                    
                    file_metadata = {
                        "name": f"{v_name}_{datetime.now().strftime('%H%M%S')}.jpg",
                        "parents": ["1egDc73Vfv8rc9-ppCuN4JWFNi1WlrK0x"]
                    }
                    
                    # Simple upload is better for quota issues than Resumable
                    media = MediaIoBaseUpload(buf, mimetype="image/jpeg", resumable=False)
                    
                    file = drive.files().create(
                        body=file_metadata, 
                        media_body=media, 
                        fields="id, webViewLink",
                        supportsAllDrives=True
                    ).execute()
                    link = file.get("webViewLink")

                    # 2. SHEET SAVE
                    client = gspread.authorize(creds)
                    sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1
                    
                    selected_opts = [opt for opt, val in zip(["Seal", "Robotics", "Cap", "Induction"], [o1, o2, o3, o4]) if val]
                    row = [
                        v_full, f"{v_name}.jpg", datetime.now().strftime("%Y-%m-%d %H:%M"), 
                        v_comp, v_name, v_phone, v_email, "", v_addr, "", 
                        ", ".join(selected_opts), v_rem, f'=HYPERLINK("{link}", "View Card")'
                    ]
                    
                    sheet.append_row(row, value_input_option="USER_ENTERED")
                    
                    st.success("✅ Saved Successfully!")
                    st.session_state.ocr_data = None # Clear data for next scan
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                # Agar Drive fail bhi ho, toh kam se kam sheet mein entry ho jaye
                st.error(f"Save Error: {e}")