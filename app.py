import streamlit as st
import os

st.title("AI Interview Analyzer")

uploaded_file = st.file_uploader(
    "Upload Interview Audio",
    type=["mp3", "wav", "m4a", "mp4"]
)

if uploaded_file:

    os.makedirs("audio", exist_ok=True)

    file_path = os.path.join(
        "audio",
        uploaded_file.name
    )

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("Audio uploaded successfully!")

    st.write("File Name:", uploaded_file.name)

    st.write("Saved To:", file_path)