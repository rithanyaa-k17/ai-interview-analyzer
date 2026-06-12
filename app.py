import streamlit as st
import os
import whisper
import re

def analyze_transcript(transcript, duration_seconds):
    filler_words = [
        "um", "uh", "umm", "uhh",
        "actually", "basically", "literally",
        "you know", "i mean", "sort of", "kind of",
        "okay", "right", "yeah", "yeahh", "hmm"
    ]

    text = transcript.lower()
    words = re.findall(r"\b\w+\b", text)
    total_words = len(words)

    filler_count = 0
    detected_fillers = {}

    # Count direct filler words/phrases
    for filler in filler_words:
        pattern = r"\b" + re.escape(filler) + r"\b"
        count = len(re.findall(pattern, text))

        if count > 0:
            detected_fillers[filler] = count
            filler_count += count

    # Handle "like" carefully
    # Count "like" only when it is NOT used as "like to", "would like", "I'd like", etc.
    like_matches = re.findall(r"\blike\b", text)
    meaningful_like_patterns = [
        r"\blike to\b",
        r"\bwould like\b",
        r"\bi'd like\b",
        r"\bi would like\b",
        r"\blike working\b",
        r"\blike using\b"
    ]

    meaningful_like_count = 0
    for pattern in meaningful_like_patterns:
        meaningful_like_count += len(re.findall(pattern, text))

    like_filler_count = max(0, len(like_matches) - meaningful_like_count)

    if like_filler_count > 0:
        detected_fillers["like"] = like_filler_count
        filler_count += like_filler_count

    # Handle "so" carefully
    # Count only when it appears at the beginning or after punctuation-like pauses
    so_count = len(re.findall(r"(^|\.\s+|,\s+)\bso\b", text))
    if so_count > 0:
        detected_fillers["so"] = so_count
        filler_count += so_count

    # Handle "well" carefully
    # Avoid counting "as well"
    well_total = len(re.findall(r"\bwell\b", text))
    as_well_count = len(re.findall(r"\bas well\b", text))
    well_filler_count = max(0, well_total - as_well_count)

    if well_filler_count > 0:
        detected_fillers["well"] = well_filler_count
        filler_count += well_filler_count

    duration_minutes = duration_seconds / 60 if duration_seconds > 0 else 1

    filler_percentage = (filler_count / total_words) * 100 if total_words > 0 else 0
    fillers_per_minute = filler_count / duration_minutes

    return total_words, filler_count, filler_percentage, fillers_per_minute, detected_fillers
def get_filler_feedback(filler_count, fillers_per_minute, duration_seconds):
    if duration_seconds < 20:
        if filler_count == 0:
            return "Clean short response. No common filler words were detected."
        elif filler_count <= 2:
            return "A few fillers appeared in a short response. This is normal and not a major concern."
        else:
            return "Several fillers appeared in a short response. Try slowing down slightly."

    if filler_count == 0:
        return "Very clean response. No common filler words were detected, though natural speech may still contain pauses."
    elif fillers_per_minute <= 2:
        return "Very natural speech. A few fillers are normal and do not affect your clarity."
    elif fillers_per_minute <= 4:
        return "Good overall. Some fillers were present, but your speech still sounds controlled."
    elif fillers_per_minute <= 6:
        return "Slightly noticeable filler usage. Try replacing some fillers with short pauses."
    elif fillers_per_minute <= 8:
        return "Moderate filler usage. Your answer may sound a little hesitant in places."
    elif fillers_per_minute <= 12:
        return "High filler usage. Practicing slower, structured answers can improve confidence."
    else:
        return "Very high filler usage. Try pausing, breathing, and organizing your answer before speaking."

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
            result = model.transcribe(file_path, initial_prompt="Transcribe the speech exactly as spoken, including filler words like um, uh, like, actually, and pauses if spoken.")
            transcript = result["text"]
            duration_seconds = 0
            if result.get("segments"):
                duration_seconds = result["segments"][-1]["end"]
            st.subheader("Transcript")
            st.write(transcript)
            total_words, filler_count, filler_percentage, fillers_per_minute, detected_fillers = analyze_transcript(transcript,duration_seconds)

            st.subheader("Communication Analysis")

            st.write("Total Words:", total_words)
            st.write("Approx Duration:", round(duration_seconds, 2), "seconds")
            st.write("Filler Words Count:", filler_count)
            st.write("Filler Percentage:", round(filler_percentage, 2), "%")
            st.write("Fillers Per Minute:", round(fillers_per_minute, 2))

            if detected_fillers:
                st.write("Detected Fillers:", detected_fillers)
            else:
                st.success("No common filler words detected in the transcript.")

            feedback = get_filler_feedback(filler_count, fillers_per_minute, duration_seconds)
            st.info(feedback)