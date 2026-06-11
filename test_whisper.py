import whisper

model = whisper.load_model("base", device="cpu")

result = model.transcribe("audio/test_audio_1.mp4")

print(result["text"])