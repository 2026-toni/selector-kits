"""
Selector de Kits OLIVA TORRAS — arquitectura por fases:
  Fase 1: tipo de kit + marca  (sin BD → ~10K tokens)
  Fase 2: selección completa   (con BD de la marca → ~20-25K tokens)
"""
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Selector de Kits · OLIVA TORRAS",
    page_icon="🔧",
    layout="centered",
)

@st.cache_resource(show_spinner="Cargando selector…")
def _warm_up():
    from selector import get_available_brands
    return get_available_brands()

available_brands = _warm_up()
from selector import chat, chat_with_image, build_system_prompt

# ── Logo ──────────────────────────────────────────────────────────────────────
logo_path = Path(__file__).parent / "logo.jpg"
if logo_path.exists():
    st.image(str(logo_path), width=200)

st.title("Selector de Kits")
st.caption("OLIVA TORRAS Mount & Drive Kits · v8 BD · v10 Prompt · claude-sonnet-4-5")

# ── Session state ─────────────────────────────────────────────────────────────
if "messages"      not in st.session_state: st.session_state.messages      = []
if "brand"         not in st.session_state: st.session_state.brand         = ""
if "phase"         not in st.session_state: st.session_state.phase         = 1

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 Filtros activos")

    # Selector de marca (se puede cambiar en cualquier momento)
    brand_options = ["(selecciona marca)"] + available_brands
    current_idx   = (brand_options.index(st.session_state.brand)
                     if st.session_state.brand in brand_options else 0)
    selected = st.selectbox("Marca del vehículo", brand_options, index=current_idx)

    if selected != "(selecciona marca)" and selected != st.session_state.brand:
        st.session_state.brand    = selected
        st.session_state.phase    = 2
        st.session_state.messages = []
        st.rerun()

    if st.session_state.brand:
        st.success(f"✅ Marca: **{st.session_state.brand}**")

    st.divider()

    st.header("📄 Adjuntar ficha técnica")
    uploaded_file = st.file_uploader(
        "Permiso de circulación / V5C",
        type=["jpg","jpeg","png","webp"],
    )

    st.divider()
    if st.button("🗑️ Nueva consulta", use_container_width=True):
        st.session_state.messages = []
        st.session_state.brand    = ""
        st.session_state.phase    = 1
        st.rerun()

# ── Mensaje de bienvenida ─────────────────────────────────────────────────────
WELCOME = """¡Hola! Soy tu asistente de selección de kits OLIVA TORRAS.

**Para empezar**, selecciona la marca del vehículo en el panel izquierdo.

Una vez seleccionada la marca, podré buscar el kit exacto para tu vehículo entre:
| Código | Tipo |
|---|---|
| **KB...** | Kit compresor A/C cabina |
| **KC...** | Kit compresor frío transporte |
| **KA...** | Kit alternador |
| **KH...** | Kit bomba hidráulica |
| **KG...** | Kit generador |
| **KF...** | Kit chasis |"""

# ── Chat history ──────────────────────────────────────────────────────────────
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

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Escribe tu consulta…")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    brand = st.session_state.brand

    if uploaded_file is not None:
        image_bytes = uploaded_file.read()
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        media_map   = {"jpg":"image/jpeg","jpeg":"image/jpeg",
                       "png":"image/png","webp":"image/webp"}
        media_type  = media_map.get(ext, "image/jpeg")
        st.session_state.messages.append({"role":"user","content":user_input})
        with st.spinner("Analizando la ficha técnica…"):
            reply = chat_with_image(
                messages=st.session_state.messages,
                image_data=image_bytes,
                media_type=media_type,
                brand=brand)
    else:
        st.session_state.messages.append({"role":"user","content":user_input})
        with st.spinner("Buscando el kit…"):
            reply = chat(messages=st.session_state.messages, brand=brand)

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.messages.append({"role":"assistant","content":reply})
