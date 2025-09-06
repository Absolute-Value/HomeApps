import io
import wave
import streamlit as st
from groq import Groq
from google import genai
from google.genai import types

# ページ設定
PAGE_TITLE = "Text To Speech"
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=":material/text_to_speech:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title(PAGE_TITLE)

# クライアント初期化
groq_client = Groq()
gen_client = genai.Client()

def wave_file_bytes(pcm, channels=1, rate=24000, sample_width=2):
    """PCMデータをWAVバイト列に変換"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()

def get_playai_voices():
    """PlayAI用のボイスリストを返す"""
    return (
        "Arista-PlayAI", "Atlas-PlayAI", "Basil-PlayAI", "Briggs-PlayAI", "Calum-PlayAI",
        "Celeste-PlayAI", "Cheyenne-PlayAI", "Chip-PlayAI", "Cillian-PlayAI", "Deedee-PlayAI",
        "Fritz-PlayAI", "Gail-PlayAI", "Indigo-PlayAI", "Mamaw-PlayAI", "Mason-PlayAI",
        "Mikail-PlayAI", "Mitch-PlayAI", "Quinn-PlayAI", "Thunder-PlayAI"
    )

def get_gemini_voices():
    """Gemini用のボイス辞書を返す"""
    return {
        "Zephyr": "Bright",
        "Puck": "Upbeat",
        "Charon": "情報が豊富",
        "Kore": "Firm",
        "Fenrir": "Excitable",
        "Leda": "Youthful",
        "Orus": "Firm",
        "Aoede": "Breezy",
        "Callirrhoe": "おおらか",
        "Autonoe": "Bright",
        "Enceladus": "Breathy",
        "Iapetus": "Clear",
        "Umbriel": "Easy-going",
        "Algieba": "Smooth",
        "Despina": "Smooth",
        "Erinome": "クリア",
        "Algenib": "Gravelly",
        "Rasalgethi": "情報が豊富",
        "Laomedeia": "アップビート",
        "Achernar": "Soft",
        "Alnilam": "Firm",
        "Schedar": "Even",
        "Gacrux": "成人向け",
        "Pulcherrima": "Forward",
        "Achird": "フレンドリー",
        "Zubenelgenubi": "カジュアル",
        "Vindemiatrix": "Gentle",
        "Sadachbia": "Lively",
        "Sadaltager": "Knowledgeable",
        "Sulafat": "Warm"
    }

def select_model_and_voice():
    """モデルとボイス、テキスト入力UIを表示し、選択値を返す"""
    model_options = ["gemini-2.5-flash-preview-tts", "playai-tts"]
    model = st.radio("model", model_options)

    if model == "playai-tts":
        voices = get_playai_voices()
        content = st.text_area('text', value='I love building and shipping new features for our users!')
        voice = st.selectbox('voice', voices)
    else:
        voices = get_gemini_voices()
        prompt = st.text_area('prompt', value='Japanese Female')
        text = st.text_area('text', value='こんばんは！')
        content = f'{prompt}: {text}'
        voice_display = [f"{k} : {v}" for k, v in voices.items()]
        voice_display_to_key = {f"{k} : {v}": k for k, v in voices.items()}
        selected_display = st.selectbox('voice', voice_display, index=5)
        voice = voice_display_to_key[selected_display]
    return model, voice, content

def generate_audio(model, voice, content, response_format="wav"):
    """選択モデルに応じて音声データを生成し、バイト列を返す"""
    if model == "playai-tts":
        response = groq_client.audio.speech.create(
            model=model,
            voice=voice,
            input=content,
            response_format=response_format
        )
        audio_bytes = b"".join(response.iter_bytes())
    else:
        response = gen_client.models.generate_content(
            model=model,
            contents=content,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    )
                ),
            )
        )
        blob = response.candidates[0].content.parts[0].inline_data.data
        audio_bytes = wave_file_bytes(blob)
    return audio_bytes

@st.fragment
def download_fragment(audio_bytes):
    st.download_button(
        label="Download wav",
        data=audio_bytes,
        file_name="output.wav",
        mime="audio/wav",
        icon=":material/download:"
    )

def main():
    model, voice, content = select_model_and_voice()
    response_format = "wav"

    if st.button("開始"):
        audio_bytes = generate_audio(model, voice, content, response_format)
        st.audio(audio_bytes, format="audio/wav")
        download_fragment(audio_bytes)

if __name__ == "__main__" or True:  # Streamlitでは直接実行されるため
    main()