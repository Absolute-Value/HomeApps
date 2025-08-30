import streamlit as st
from groq import Groq

PAGE_TITLE = "Text To Speech"
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=":material/text_to_speech:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title(PAGE_TITLE)

client = Groq()
MODEL_OPTIONS = ("playai-tts", "playai-tts-arabic")
VOICE_OPTIONS = ("Arista-PlayAI", "Atlas-PlayAI", "Basil-PlayAI", "Briggs-PlayAI", "Calum-PlayAI", "Celeste-PlayAI", "Cheyenne-PlayAI", "Chip-PlayAI", "Cillian-PlayAI", "Deedee-PlayAI", "Fritz-PlayAI", "Gail-PlayAI", "Indigo-PlayAI", "Mamaw-PlayAI", "Mason-PlayAI", "Mikail-PlayAI", "Mitch-PlayAI", "Quinn-PlayAI", "Thunder-PlayAI")
ARABIC_VOICE_OPTIONS = ("Ahmad-PlayAI", "Amira-PlayAI", "Khalid-PlayAI", "Nasser-PlayAI")

model = st.radio("model", MODEL_OPTIONS)
if model == "playai-tts":
    voices = VOICE_OPTIONS
else:
    voices = ARABIC_VOICE_OPTIONS
voice = st.selectbox('voice', voices)
text = st.text_area('text', value='I love building and shipping new features for our users!')
response_format = "wav"

if st.button("開始"):
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format=response_format
    )
    audio_bytes = b"".join(response.iter_bytes())
    st.audio(audio_bytes, format="audio/wav")

    @st.fragment
    def download_fragment(audio_bytes):
        st.download_button(
            label="Download wav",
            data=audio_bytes,
            file_name="output.wav",
            mime="audio/wav",
            icon=":material/download:"
        )
    
    download_fragment(audio_bytes)