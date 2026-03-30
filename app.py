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
import requests
import base64
import os

# ================= PAGE CONFIG =================
st.set_page_config(page_title="EDW Business Card Scanner", layout="centered")

# --- Helper Functions ---
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

def upload_to_imgbb(image):
    try:
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=50)
        img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
        api_key = st.secrets["imgbb_api_key"]
        url = "https://api.imgbb.com/1/upload"
        data = {"key": api_key, "image": img_str}
        response = requests.post(url, data=data)
        return response.json()['data']['url']
    except:
        return "Upload Error"

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

# ================= SESSION STATE =================
if "ocr_data" not in st.session_state:
    st.session_state.ocr_data = None
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0 

# ================= UI INTERFACE =================
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=100)
with col_title:
    st.markdown("<h2 style='text-align:left; color:#1E3A8A; margin-top:10px;'>ELECTRONICS DEVICES WORLDWIDE PVT. LTD.</h2>", unsafe_allow_html=True)

st.divider()

# Uploader with Reset Key
uploaded = st.file_uploader("📸 Upload Visiting Card Image", type=["jpg","png","jpeg"], key=f"uploader_{st.session_state.uploader_key}")

# AUTO SCAN
if uploaded and st.session_state.ocr_data is None:
    img = Image.open(uploaded)
    img = fix_orientation(img)
    with st.spinner("AI scanning card..."):
        st.session_state.ocr_data = extract_details(img)
        st.rerun()

if uploaded and st.session_state.ocr_data:
    img = Image.open(uploaded)
    img = fix_orientation(img)
    st.image(img, width=350, caption="Uploaded Card")
    
    d = st.session_state.ocr_data
    with st.form("entry_form", clear_on_submit=True):
        st.subheader("Verify Details")
        v_full = st.text_area("Full OCR Text", value=d["full"], height=100)
        
        c1, c2 = st.columns(2)
        v_name = c1.text_input("Person Name", value=d["name"])
        v_phone = c1.text_input("Phone Number", value=d["phone"])
        v_email = c1.text_input("Email ID", value=d["email"])
        v_comp = c2.text_input("Company Name", value=d["comp"])
        v_web = c2.text_input("Website", value="")
        v_addr = c2.text_area("Office Address", value=d["addr"])

        st.write("---")
        st.subheader("Inspection Options")
        col_a, col_b = st.columns(2)
        o1 = col_a.checkbox("Seal Integrity")
        o2 = col_a.checkbox("Robotics")
        o3 = col_b.checkbox("Cap and Clouser")
        o4 = col_b.checkbox("Induction Capsealing")
        v_rem = st.text_area("Remarks")
        
        if st.form_submit_button("🚀 Final Confirm & Save EVERYTHING"):
            try:
                with st.spinner("Processing..."):
                    img_url = upload_to_imgbb(img)
                    
                    creds_dict = {
                        "type": st.secrets["gcp_service_account"]["type"],
                        "project_id": st.secrets["gcp_service_account"]["project_id"],
                        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                        "private_key": st.secrets["gcp_service_account"]["private_key"],
                        "client_email": st.secrets["gcp_service_account"]["client_email"],
                        "client_id": st.secrets["gcp_service_account"]["client_id"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{st.secrets['gcp_service_account']['client_email']}"
                    }
                    
                    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"])
                    client = gspread.authorize(creds)
                    sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1
                    
                    # --- FIX: Yahan poore naam likhe hain taaki sheet mein sahi jaye ---
                    names_list = ["Seal Integrity", "Robotics", "Cap and Clouser", "Induction Capsealing"]
                    bool_list = [o1, o2, o3, o4]
                    selected_opts = [name for name, val in zip(names_list, bool_list) if val]
                    
                    row = [v_full, f"{v_name}.jpg", datetime.now().strftime("%Y-%m-%d %H:%M"), 
                           v_comp, v_name, v_phone, v_email, "", v_addr, v_web, 
                           ", ".join(selected_opts), v_rem, f'=HYPERLINK("{img_url}", "View Card Photo")']
                    
                    sheet.append_row(row, value_input_option="USER_ENTERED")
                    
                    st.success("✅ DATA SAVED SUCCESSFULLY!")
                    st.balloons()
                    
                    st.session_state.ocr_data = None 
                    st.session_state.uploader_key += 1 
                    
                    time.sleep(2)
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Save Error: {e}")