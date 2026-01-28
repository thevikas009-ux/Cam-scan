# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Image to Google Sheet", layout="centered")

# ---------------- HEADER (FIXED LOGO + COMPANY NAME) ----------------
LOGO_URL = "https://drive.google.com/uc?export=view&id=1xq5ehfCCw8Ncv5FxS845Oxh0eAjxR5-I"

col1, col2 = st.columns([1, 4])

with col1:
    st.image(LOGO_URL, width=80)   # 👈 FIXED SIZE (WORKING)

with col2:
    st.markdown(
        """
        <div style="padding-top:10px">
            <h3 style="margin-bottom:0;">
                ELECTRONICS DEVICES WORLDWIDE PVT. LTD.
            </h3>
            <p style="margin-top:2px;color:gray;">
                Smart OCR • Image to Google Sheet
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

st.title("📸 Image to Google Sheet App")
