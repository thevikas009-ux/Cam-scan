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
        if "imgbb_api_key" not in st.secrets:
            st.error("Secrets mein 'imgbb_api_key' nahi mila!")
            return "Key Missing"
            
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=50)
        img_str = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        api_key = st.secrets["imgbb_api_key"]
        url = "https://api.imgbb.com/1/upload"
        data = {"key": api_key, "image": img_str}
        
        response = requests.post(url, data=data)
        res_json = response.json()
        
        if response.status_code == 200:
            return res_json['data']['url']
        else:
            return "Upload Failed"
    except Exception as e:
        return f"Error: {e}"

def extract_details(image):
    try:
        full_text = pytesseract.image_to_string(image)
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        email = re.findall(r"\S+@\S+", full_text)
        phone = re.findall(r"\+?\d[\d\s\-]{8,15}", full_text)
        
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
    except: return None

# ================= UI INTERFACE =================
col_logo, col_title = st.columns([1, 4])

with col_logo:
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        st.image(Image.open(logo_path), width=100)
    else:
        st.warning("Logo missing")

with col_title:
    st.markdown("<h2 style='text-align:left; color:#1E3A8A; margin-top:10px;'>ELECTRONICS DEVICES WORLDWIDE PVT. LTD.</h2>", unsafe_allow_html=True)

st.divider()

if "ocr_data" not in st.session_state: 
    st.session_state.ocr_data = None

uploaded = st.file_uploader("📸 Upload Visiting Card Image", type=["jpg","png","jpeg"])

# AUTO SCAN LOGIC
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
    with st.form("entry_form"):
        st.subheader("Verify Details")
        v_full = st.text_area("Full OCR Text (A)", value=d["full"], height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            v_name = st.text_input("Person Name", value=d["name"])
            v_phone = st.text_input("Phone Number", value=d["phone"])
            v_email = st.text_input("Email ID", value=d["email"])
        with col2:
            v_comp = st.text_input("Company Name", value=d["comp"])
            v_web = st.text_input("Website (if any)", value="")
            v_addr = st.text_area("Office Address", value=d["addr"])

        st.write("---")
        st.subheader("Inspection Options")
        col_a, col_b = st.columns(2)
        o1 = col_a.checkbox("Seal Integrity")
        o2 = col_a.checkbox("Robotics")
        o3 = col_b.checkbox("Cap and Clouser")
        o4 = col_b.checkbox("Induction Capsealing")
        
        v_rem = st.text_area("Remarks / Note")
        
        # --- SAVE BUTTON LOGIC ---
        if st.form_submit_button("🚀 Final Confirm & Save EVERYTHING"):
            try:
                with st.spinner("Processing... Please wait."):
                    # 1. ImgBB Upload
                    img_url = upload_to_imgbb(img)
                    
                    # 2. Sheets Setup
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
                    
                    opts = [opt for opt, val in zip(["Seal", "Robotics", "Cap", "Induction"], [o1, o2, o3, o4]) if val]
                    
                    row = [
                        v_full, f"{v_name}.jpg", datetime.now().strftime("%Y-%m-%d %H:%M"), 
                        v_comp, v_name, v_phone, v_email, "", v_addr, v_web, 
                        ", ".join(opts), v_rem, f'=HYPERLINK("{img_url}", "View Card Photo")'
                    ]
                    
                    sheet.append_row(row, value_input_option="USER_ENTERED")
                    
                    # --- SUCCESS AND AUTO RESET ---
                    st.success("✅ DATA SAVED SUCCESSFULLY IN GOOGLE SHEET!")
                    st.balloons()
                    
                    # Clear session state
                    st.session_state.ocr_data = None 
                    
                    # Wait for 3 seconds so user can see success message
                    time.sleep(3)
                    
                    # Refresh page
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Save Error: {e}")