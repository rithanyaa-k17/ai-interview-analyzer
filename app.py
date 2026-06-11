import streamlit as st
import os
import whisper

st.title("AI Interview Analyzer")

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base", device="cpu")

uploaded_file = st.file_uploader(
    "Upload Interview Audio",
    type=["mp3", "wav", "m4a", "mp4"]
)

if uploaded_file:
    os.makedirs("audio", exist_ok=True)

    file_path = os.path.join("audio", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("Audio uploaded successfully!")
    st.write("File Name:", uploaded_file.name)
    st.write("Saved To:", file_path)

    if st.button("Transcribe Audio"):
        with st.spinner("Transcribing audio... Please wait."):
            model = load_whisper_model()
            result = model.transcribe(file_path)

        st.subheader("Transcript")
        st.write(result["text"])