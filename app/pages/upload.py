import os
import uuid
import streamlit as st
from PIL import Image

IMAGES_DIR = "/data/images"
os.makedirs(IMAGES_DIR, exist_ok=True)

def main():
    if "file_uploader_key" not in st.session_state:
        st.session_state["file_uploader_key"] = 0
    if "rotation_angle" not in st.session_state:
        st.session_state["rotation_angle"] = 0
    st.title("レシート登録ページ")

    file_count = len([f for f in os.listdir(IMAGES_DIR) if os.path.isfile(os.path.join(IMAGES_DIR, f))])
    st.metric("Wait", file_count, 0, border=True)

    if st.button("更新"):
        st.rerun()
    
    uploaded_file = st.file_uploader(
        "画像を選択してください",
        type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'],
        key=st.session_state["file_uploader_key"],
    )
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        max_width, max_height = 1920, 1080
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height))
        filename = f"{uuid.uuid4()}.jpg"
        save_path = os.path.join(IMAGES_DIR, filename)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("左回転"):
                st.session_state["rotation_angle"] = (st.session_state["rotation_angle"] - 90) % 360
        with col2:
            if st.button("右回転"):
                st.session_state["rotation_angle"] = (st.session_state["rotation_angle"] + 90) % 360

        rotated_image = image.rotate(-st.session_state["rotation_angle"], expand=True)
        st.image(rotated_image, caption=f"回転角度: {st.session_state['rotation_angle']}°", use_container_width=True)
        image = rotated_image

        if st.button("保存"):
            image.save(save_path, format="JPEG")
            st.toast(f"画像を保存しました: {uploaded_file.name} -> {save_path}")

            st.session_state["file_uploader_key"] += 1
            st.rerun()

if __name__ == "__main__":
    main()