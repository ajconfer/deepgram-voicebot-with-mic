
import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, ClientSettings
import av
import os
import tempfile
import requests

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

st.title("🎙️ Speak to Deepgram VoiceBot")
st.write("Press 'Start' to record your question. We'll transcribe it with Deepgram and reply using GPT.")

# Audio processing class to capture mic input
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.recorded_frames = []

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        self.recorded_frames.append(frame)
        return frame

ctx = webrtc_streamer(
    key="mic",
    mode="sendonly",
    client_settings=ClientSettings(media_stream_constraints={"audio": True, "video": False}),
    audio_processor_factory=AudioProcessor,
    async_processing=True,
)

if ctx and ctx.state.playing:
    st.info("Recording... Speak now.")
elif ctx and not ctx.state.playing and hasattr(ctx, "audio_processor"):
    audio_frames = ctx.audio_processor.recorded_frames
    if audio_frames:
        st.success("Recording complete. Processing...")

        # Save to temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
            with av.open(f.name, 'w', format='wav') as container:
                stream = container.add_stream("pcm_s16le")
                for frame in audio_frames:
                    container.mux(frame)

        # Transcribe with Deepgram
        with open(wav_path, 'rb') as audio_file:
            response = requests.post(
                "https://api.deepgram.com/v1/listen",
                headers={
                    "Authorization": f"Token {DEEPGRAM_API_KEY}",
                    "Content-Type": "audio/wav"
                },
                data=audio_file
            )

        if response.status_code != 200:
            st.error("Transcription failed: " + response.text)
        else:
            transcript = response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
            st.markdown(f"**Transcript:** {transcript}")

            # Get response from GPT
            prompt = f"You are a helpful contact center AI assistant. A customer just said: '{transcript}'. How should you respond?"

            openai_response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5
                }
            )

            if openai_response.status_code != 200:
                st.error("OpenAI API failed: " + openai_response.text)
            else:
                reply = openai_response.json()["choices"][0]["message"]["content"]
                st.markdown(f"**VoiceBot Reply:** {reply}")
