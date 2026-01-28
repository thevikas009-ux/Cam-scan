# ---------------- FILE UPLOAD OR CAMERA ----------------
uploaded_file = st.file_uploader(
    "Upload image (jpg / png / jpeg)",
    type=["jpg", "png", "jpeg"]
)

camera_image = st.camera_input("Or take a picture with your camera")

# Use whichever the user provided
image_file = uploaded_file or camera_image

if image_file:
    image = Image.open(io.BytesIO(image_file.read()))
    st.image(image, use_column_width=True)

    # OCR extraction
    text = extract_text(image)

    st.subheader("Extracted Text")
    st.text_area("OCR Output", text, height=200)

    if st.button("Save to Google Sheet"):
        try:
            company, name, phone, email, designation, address = extract_fields(text)
            
            sheet.append_row([
                company,
                name,
                phone,
                email,
                designation,
                address,
                image_file.name if uploaded_file else "Camera Capture",
                str(datetime.now())
            ])
            st.success("✅ Data saved to Google Sheet")
        except Exception as e:
            st.error(f"Error saving to Sheet: {e}")
