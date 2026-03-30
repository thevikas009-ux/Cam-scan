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

# ================= PAGE CONFIG (Restore Original) =================
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
        
        # Address Keywords
        addr_keywords = ["road", "street", "floor", "building", "plot", "area", "nagar", "city", "sector", "industrial", "phase"]
        addr_list = [line for line in lines if any(w in line.lower() for w in addr_keywords) or re.search(r"\b\d{6}\b", line)]
        
        return {
            "full": full_text, 
            "name": lines[0] if lines else "Unknown",
            "phone": phone[0] if phone else "", 
            "email": email[0] if email else "",
            "addr": ", ".join(addr_list),
            "comp": next((l for l in lines if "pvt" in l.lower() or "ltd" in l.lower()), "")
        }
    except Exception as e:
        st.error(f"OCR Error: {e}")
        return None

# ================= RESTORE HEADERS & INTERFACE =================
st.markdown("<h2 style='text-align:center; color:#1E3A8A;'>ELECTRONICS DEVICES WORLDWIDE PVT. LTD.</h2>", unsafe_allow_html=True)
st.divider()

if "ocr_data" not in st.session_state:
    st.session_state.ocr_data = None

uploaded = st.file_uploader("📸 Upload Visiting Card", type=["jpg","png","jpeg"])

if uploaded:
    img = Image.open(uploaded)
    img = fix_orientation(img)
    st.image(img, width=350, caption="Uploaded Card Image")

    if st.button("🔍 Step 1: Scan Card Details"):
        with st.spinner("Reading card with Tesseract..."):
            st.session_state.ocr_data = extract_details(img)
            st.rerun()

    if st.session_state.ocr_data:
        d = st.session_state.ocr_data
        
        # Form logic to prevent reload crashes
        with st.form("entry_form"):
            st.subheader("📝 Step 2: Verify & Edit Details")
            
            v_full = st.text_area("Full OCR Text (A)", value=d["full"], height=120)
            
            col1, col2 = st.columns(2)
            with col1:
                v_name = st.text_input("Person Name", value=d["name"])
                v_phone = st.text_input("Phone Number", value=d["phone"])
                v_email = st.text_input("Email ID", value=d["email"])
            with col2:
                v_comp = st.text_input("Company Name", value=d["comp"])
                v_web = st.text_input("Website (if any)", value="")
                v_addr = st.text_area("Office Address", value=d.get("addr", ""))

            st.write("---")
            st.subheader("⚙️ Step 3: Inspection Options")
            c1, c2 = st.columns(2)
            o1 = c1.checkbox("Seal Integrity")
            o2 = c1.checkbox("Robotics")
            o3 = c2.checkbox("Cap and Clouser")
            o4 = c2.checkbox("Induction Capsealing")
            
            v_remarks = st.text_area("Remarks / Note")

            if st.form_submit_button("🚀 Step 4: Final Confirm & Save Everything"):
                try:
                    with st.spinner("Processing..."):
                        # Credentials for both Drive and Sheets
                        creds = service_account.Credentials.from_service_account_info(
                            st.secrets["gcp_service_account"], 
                            scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
                        )
                        
                        # 1. DRIVE UPLOAD (Returning photo feature but light-weight)
                        drive = build("drive", "v3", credentials=creds)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=60) # High compression to save RAM
                        buf.seek(0)
                        
                        folder_id = "1egDc73Vfv8rc9-ppCuN4JWFNi1WlrK0x"
                        file_name = f"{v_name}_{datetime.now().strftime('%H%M%S')}.jpg"
                        meta = {"name": file_name, "parents": [folder_id]}
                        media = MediaIoBaseUpload(buf, mimetype="image/jpeg", resumable=True)
                        
                        file = drive.files().create(body=meta, media_body=media, fields="webViewLink", supportsAllDrives=True).execute()
                        link = file.get("webViewLink")

                        # 2. SHEET SAVE (Column A to M)
                        client = gspread.authorize(creds)
                        sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1
                        
                        opts = [opt for opt, val in zip(["Seal Integrity", "Robotics", "Cap and Clouser", "Induction Capsealing"], [o1, o2, o3, o4]) if val]
                        
                        row = [
                            v_full, file_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                            v_comp, v_name, v_phone, v_email, "", v_addr, v_web, 
                            ", ".join(opts), v_remarks, f'=HYPERLINK("{link}", "View Card")'
                        ]
                        
                        sheet.append_row(row, value_input_option="USER_ENTERED")
                        
                        st.success("✅ Saved Successfully! Image uploaded to Drive.")
                        st.balloons()
                        st.session_state.ocr_data = None
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error during save: {e}")