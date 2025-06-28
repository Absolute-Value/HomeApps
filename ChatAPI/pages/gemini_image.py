import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

st.set_page_config(
    page_title="Gemini 画像生成",
    page_icon=":robot:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title("Gemini 画像生成")

client = genai.Client()

if prompt := st.chat_input("画像生成のプロンプトを入力してください..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    response = client.models.generate_content(
        model="gemini-2.0-flash-preview-image-generation",
        contents=(prompt),
        config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
        )
    )

    with st.chat_message("assistant"):
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                st.write(part.text)
            elif part.inline_data is not None:
                image = Image.open(BytesIO((part.inline_data.data)))
                st.image(image)