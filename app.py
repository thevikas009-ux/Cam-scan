import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime
import re
import pytesseract
from PIL import Image
import time

# ================= PAGE CONFIG =================
st.set_page_config(page_title="EDW OCR - Sheet Only", layout="centered")

def extract_details(image):
    try:
        # Pytesseract light-weight scan
        full_text = pytesseract.image_to_string(image)
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]
        email = re.findall(r"\S+@\S+", full_text)
        phone = re.findall(r"\+?\d[\d\s\-]{8,15}", full_text)
        return {
            "full": full_text, 
            "name": lines[0] if lines else "Unknown",
            "phone": phone[0] if phone else "", 
            "email": email[0] if email else "",
            "comp": next((l for l in lines if "pvt" in l.lower() or "ltd" in l.lower()), "")
        }
    except Exception as e:
        st.error(f"OCR Error: {e}")
        return None

# ================= UI =================
st.title("📑 EDW Sheet Entry (Text Only)")

if "ocr_data" not in st.session_state:
    st.session_state.ocr_data = None

uploaded = st.file_uploader("Upload Card Image", type=["jpg","png","jpeg"])

if uploaded:
    img = Image.open(uploaded)
    st.image(img, width=300)

    if st.button("🔍 Scan Card"):
        with st.spinner("Reading text..."):
            st.session_state.ocr_data = extract_details(img)
            st.rerun()

    if st.session_state.ocr_data:
        d = st.session_state.ocr_data
        with st.form("sheet_form"):
            v_name = st.text_input("Name", value=d["name"])
            v_phone = st.text_input("Phone", value=d["phone"])
            v_email = st.text_input("Email", value=d["email"])
            v_comp = st.text_input("Company", value=d["comp"])
            v_rem = st.text_area("Remarks")
            
            if st.form_submit_button("🚀 Save to Sheet"):
                try:
                    creds = service_account.Credentials.from_service_account_info(
                        st.secrets["gcp_service_account"], 
                        scopes=["https://www.googleapis.com/auth/spreadsheets"]
                    )
                    client = gspread.authorize(creds)
                    sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1
                    
                    row = [d["full"], "No Photo", datetime.now().strftime("%Y-%m-%d"), 
                           v_comp, v_name, v_phone, v_email, "", "", "", "", v_rem, "No Link"]
                    
                    sheet.append_row(row, value_input_option="USER_ENTERED")
                    st.success("✅ Saved in Google Sheet!")
                    st.session_state.ocr_data = None
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Sheet Error: {e}")