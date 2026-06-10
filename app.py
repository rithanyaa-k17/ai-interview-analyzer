import streamlit as st

st.title("AI Interview Analyzer")

uploaded_file = st.file_uploader(
    "Upload Interview Audio",
    type=["mp3", "wav", "m4a"]
)

if uploaded_file:
    st.success("Audio uploaded successfully!")