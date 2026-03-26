import streamlit as st
import easyocr
import numpy as np
from PIL import Image
import gspread
from google.oauth2 import service_account
from datetime import datetime
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Page Setup
st.set_page_config(page_title="OCR App", layout="centered")
st.title("📸 Visiting Card OCR")

# ================= OCR LOAD =================
@st.cache_resource
def load_reader():
    return easyocr.Reader(["en"], gpu=False)

reader = load_reader()

def run_ocr(image):
    img = np.array(image.convert("RGB"))
    results = reader.readtext(img, detail=0)
    return "\n".join(results)

# ================= GOOGLE AUTH =================
def get_creds():
    return service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

# ================= DRIVE UPLOAD =================
def upload_to_drive(image, file_name):
    try:
        creds = get_creds()
        service = build("drive", "v3", credentials=creds)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)

        file_metadata = {
            "name": file_name,
            "parents": ["1EVIcT6ewpzYJ_yD2lTahH2Ld-neJj2Ce"] # Aapka Folder ID
        }

        media = MediaIoBaseUpload(buffer, mimetype="image/jpeg", resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        return file.get("webViewLink")

    except Exception as e:
        # Screen par error dikhayega agar upload fail hua
        st.error(f"❌ Drive Error: {e}")
        return "No Link"

# ================= UI & LOGIC =================
uploaded = st.file_uploader("Upload visiting card", type=["jpg","png","jpeg"])

if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Uploaded Image", use_container_width=True)

    with st.spinner("Extracting text..."):
        full_text = run_ocr(image)
    
    st.subheader("Extracted Details")
    ocr_result = st.text_area("OCR Text", full_text, height=150)

    # Manual Inputs
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name")
    with col2:
        remarks = st.text_input("Remarks")

    # --- AGAR AAPKO 4 OPTIONS CHAHIYE THE ---
    business_type = st.radio("Business Type", ["Retailer", "Wholesaler", "Distributor", "Manufacturer"], horizontal=True)

    if st.button("🚀 Save to Google Sheets"):
        if not name:
            st.warning("Pehle Name bhariye!")
        else:
            with st.spinner("Saving data..."):
                # 1. Upload Image to Drive
                file_name = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                drive_link = upload_to_drive(image, file_name)

                # 2. Connect to Sheet
                try:
                    creds = get_creds()
                    client = gspread.authorize(creds)
                    sheet = client.open_by_key(st.secrets["sheet_id"]).worksheet("Sheet1")

                    # Clickable Link Formula
                    clickable_link = f'=HYPERLINK("{drive_link}", "View Image")'

                    # 3. Prepare Data Row (Total 7 Columns)
                    new_row = [
                        full_text,      # Col A
                        file_name,      # Col B
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # Col C
                        name,           # Col D
                        business_type,  # Col E (Naya Option)
                        remarks,        # Col F
                        clickable_link  # Col G
                    ]

                    # 4. Append to Sheet (Fixes Shifting)
                    sheet.append_row(new_row, value_input_option="USER_ENTERED")

                    st.success("✅ Success! Data added to Sheet and Image saved to Drive.")
                    st.write(f"🔗 Drive Link: {drive_link}")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Sheet Error: {e}")