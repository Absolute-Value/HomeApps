import streamlit as st
from google import genai
from PIL import Image

st.set_page_config(
    page_title="Gemini",
    page_icon=":robot:",
    initial_sidebar_state="expanded",
    layout="wide",
)
st.title("Gemini")

client = genai.Client()

with st.sidebar:
    model_options = {
        "Gemini-2.5-Flash-Lite": "gemini-2.5-flash-lite-preview-06-17",
        "Gemini-2.5-Flash": "gemini-2.5-flash",
    }
    selected_label = st.selectbox(":gear: モデル選択", list(model_options.keys()))
    st.session_state["model_name"] = model_options[selected_label]

if prompt := st.chat_input("質問してみましょう", accept_file=True):
    with st.chat_message("user"):
        st.markdown(prompt.text)
        if prompt["files"]:
            st.image(prompt["files"][0])
    
    with st.chat_message("assistant"):
        contents = [prompt.text]
        if prompt["files"]:
            image = Image.open(prompt["files"][0])
            contents.append(image)
        stream = client.models.generate_content_stream(
            model=st.session_state["model_name"],
            contents=contents
        )

        response = ""
        with st.empty():
            for chunk in stream:
                response += chunk.text
                st.write(response)