import streamlit as st
from groq import Groq
from io import BytesIO

PAGE_TITLE = "Speech To Text"
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=":material/speech_to_text:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title(PAGE_TITLE)

client = Groq()
MODEL_OPTIONS = ("whisper-large-v3", "whisper-large-v3-turbo")
LANGUAGE_OPTIONS = (None, 'en', 'ja')
model = st.radio("model", MODEL_OPTIONS)
language = st.selectbox("言語", LANGUAGE_OPTIONS)
temperature = st.slider("temperature", 0.0, 1.0, value=0.0)

uploaded_file = st.file_uploader("音声ファイルをアップロード")

if uploaded_file is not None:
    audio_file = BytesIO(uploaded_file.getvalue())
    audio_file.name = uploaded_file.name
    transcription = client.audio.transcriptions.create(
        file=audio_file,
        model=model,
        language=language,
        temperature=temperature,
        response_format="verbose_json",
    )
    st.write(transcription.text)