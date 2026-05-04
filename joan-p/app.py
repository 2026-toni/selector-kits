"""
Streamlit front-end for the OLIVA TORRAS Kit Selector.
Relies on selector.py which loads bbdd_kits_v8.xlsx + prompt_selector_kits_v10.md
and calls claude-sonnet-4-20250514 via the Anthropic SDK.
"""

import streamlit as st
from pathlib import Path
from selector import chat, chat_with_image

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Joan P. · Selector de Kits",
    page_icon="🔧",
    layout="centered",
)

# ── Logo ──────────────────────────────────────────────────────────────────────
logo_path = Path(__file__).parent / "logo.jpg"
if logo_path.exists():
    st.image(str(logo_path), width=220)

st.title("Joan P. · Selector de Kits")
st.caption("OLIVA TORRAS Mount & Drive Kits — v8 BD · v10 Prompt · claude-sonnet-4")

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # content may be str or list (when an image was attached)
        if isinstance(msg["content"], str):
            st.markdown(msg["content"])
        else:
            # multipart: render text blocks only
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    st.markdown(block["text"])

# ── Sidebar: image upload + reset ─────────────────────────────────────────────
with st.sidebar:
    st.header("📄 Adjuntar ficha técnica")
    uploaded_file = st.file_uploader(
        "Sube el permiso de circulación o V5C",
        type=["jpg", "jpeg", "png", "webp"],
        help="El asistente extraerá los datos automáticamente.",
    )
    st.divider()
    if st.button("🗑️ Nueva consulta", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Escribe tu consulta…")

if user_input:
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build message for the API
    if uploaded_file is not None:
        image_bytes = uploaded_file.read()
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        media_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        media_type = media_map.get(ext, "image/jpeg")

        # Store user message with image indicator in history (text-only for display)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Call API with image
        with st.spinner("Joan P. está analizando la ficha…"):
            reply = chat_with_image(
                messages=st.session_state.messages,
                image_data=image_bytes,
                media_type=media_type,
            )
        # Clear the uploader after use (reset via rerun on next interaction)
    else:
        # Plain text message
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.spinner("Joan P. está buscando el kit…"):
            reply = chat(messages=st.session_state.messages)

    # Display and store assistant reply
    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
