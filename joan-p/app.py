"""
Streamlit front-end — Selector de Kits OLIVA TORRAS
"""

import streamlit as st
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Selector de Kits · OLIVA TORRAS",
    page_icon="🔧",
    layout="centered",
)

# ── Pre-warm: build system prompt on first load (shows spinner, not blank) ────
@st.cache_resource(show_spinner="⏳ Cargando base de datos… (solo la primera vez)")
def _warm_up():
    from selector import get_system_prompt
    get_system_prompt()
    return True

_warm_up()

from selector import chat, chat_with_image

# ── Logo + header ─────────────────────────────────────────────────────────────
logo_path = Path(__file__).parent / "logo.jpg"
if logo_path.exists():
    st.image(str(logo_path), width=200)

st.title("Selector de Kits")
st.caption("OLIVA TORRAS Mount & Drive Kits · v8 BD · v10 Prompt · claude-sonnet-4")

# ── Welcome message (shown only when conversation is empty) ──────────────────
WELCOME = """¡Hola! Soy tu asistente de selección de kits OLIVA TORRAS.

¿Qué tipo de kit necesitas?

| Código | Tipo | Descripción |
|---|---|---|
| **KB...** | Kit compresor A/C | Compresor de aire acondicionado de cabina |
| **KC...** | Kit compresor frío industrial | Compresor de frío de transporte |
| **KA...** | Kit alternador | Alternador auxiliar |
| **KH...** | Kit bomba hidráulica | Bomba hidráulica |
| **KG...** | Kit generador | Generador eléctrico |
| **KF...** | Kit chasis | Adaptación de chasis |

Escribe el tipo de kit o cualquier dato del vehículo para empezar."""

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render conversation ───────────────────────────────────────────────────────
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(WELCOME)
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            if isinstance(content, str):
                st.markdown(content)
            else:
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        st.markdown(block["text"])

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📄 Adjuntar ficha técnica")
    uploaded_file = st.file_uploader(
        "Permiso de circulación / V5C",
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
    with st.chat_message("user"):
        st.markdown(user_input)

    if uploaded_file is not None:
        image_bytes = uploaded_file.read()
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        media_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                     "png": "image/png", "webp": "image/webp"}
        media_type = media_map.get(ext, "image/jpeg")

        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.spinner("Analizando la ficha técnica…"):
            reply = chat_with_image(
                messages=st.session_state.messages,
                image_data=image_bytes,
                media_type=media_type,
            )
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.spinner("Buscando el kit…"):
            reply = chat(messages=st.session_state.messages)

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
