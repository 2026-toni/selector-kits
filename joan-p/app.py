"""
Selector de Kits OLIVA TORRAS
Arquitectura: Marca → Tipo de Kit → BD específica (~2K tokens)
UI: industrial/professional con upload de documentos avanzado
"""
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Selector de Kits · OLIVA TORRAS",
    page_icon="🔧",
    layout="centered",
)

# ── Custom CSS — industrial/professional aesthetic ────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Barlow:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Barlow', sans-serif;
}
.stApp { background: #f4f3f0; }

/* Header */
.main-header {
    background: #1a1a1a;
    color: #f4f3f0;
    padding: 1.5rem 2rem;
    margin: -1rem -1rem 2rem -1rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    border-bottom: 3px solid #e8431a;
}
.main-header h1 {
    font-size: 1.4rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.main-header p {
    font-size: 0.75rem;
    color: #999;
    margin: 0;
    font-family: 'DM Mono', monospace;
}

/* Phase indicators */
.phase-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
}
.phase-item {
    padding: 0.3rem 0.8rem;
    border: 1px solid #ccc;
    background: white;
    color: #999;
    border-radius: 2px;
}
.phase-item.active {
    background: #e8431a;
    color: white;
    border-color: #e8431a;
    font-weight: 500;
}
.phase-item.done {
    background: #1a1a1a;
    color: #f4f3f0;
    border-color: #1a1a1a;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #1a1a1a;
}
section[data-testid="stSidebar"] * {
    color: #f4f3f0 !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] h2, 
section[data-testid="stSidebar"] h3 {
    color: #f4f3f0 !important;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.1em;
}
section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #2a2a2a !important;
    border-color: #444 !important;
    color: #f4f3f0 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background: #e8431a !important;
    color: white !important;
    border: none !important;
    border-radius: 2px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}
section[data-testid="stSidebar"] .stFileUploader {
    background: #2a2a2a;
    border: 1px dashed #444;
    border-radius: 4px;
    padding: 0.5rem;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: white;
    border: 1px solid #e8e8e4;
    border-radius: 4px;
    margin-bottom: 0.75rem;
    padding: 1rem !important;
}

/* Document preview badge */
.doc-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: #fff3f0;
    border: 1px solid #e8431a;
    color: #e8431a;
    padding: 0.3rem 0.7rem;
    border-radius: 2px;
    font-size: 0.75rem;
    font-family: 'DM Mono', monospace;
    margin-bottom: 0.5rem;
}

/* Token cost indicator */
.cost-indicator {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    color: #999;
    text-align: right;
    padding: 0.2rem 0;
}
</style>
""", unsafe_allow_html=True)


# ── Load resources ────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Iniciando selector…")
def _init():
    from selector import get_available_brands
    return get_available_brands()

available_brands = _init()
from selector import chat, chat_with_image, get_kit_types_for_brand

# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    "messages": [], "brand": "", "kit_type": "",
    "phase": 1, "pending_image": None, "pending_media_type": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    logo_path = Path(__file__).parent / "logo.jpg"
    if logo_path.exists():
        st.image(str(logo_path), width=160)

    st.markdown("### 🏷 Marca")
    brand_options = ["— Selecciona marca —"] + available_brands
    brand_idx = (brand_options.index(st.session_state.brand)
                 if st.session_state.brand in brand_options else 0)
    selected_brand = st.selectbox("Marca del vehículo", brand_options,
                                  index=brand_idx, label_visibility="collapsed")

    if selected_brand != "— Selecciona marca —" and selected_brand != st.session_state.brand:
        st.session_state.brand    = selected_brand
        st.session_state.kit_type = ""
        st.session_state.phase    = 2
        st.session_state.messages = []
        st.rerun()

    if st.session_state.brand:
        st.markdown("### 🔩 Tipo de Kit")
        kits = get_kit_types_for_brand(st.session_state.brand)
        kit_options = ["— Selecciona tipo —"] + kits
        kit_idx = (kit_options.index(st.session_state.kit_type)
                   if st.session_state.kit_type in kit_options else 0)
        selected_kit = st.selectbox("Tipo de kit", kit_options,
                                    index=kit_idx, label_visibility="collapsed")

        if selected_kit != "— Selecciona tipo —" and selected_kit != st.session_state.kit_type:
            st.session_state.kit_type = selected_kit
            st.session_state.phase    = 3
            st.session_state.messages = []
            st.rerun()

    st.divider()

    st.markdown("### 📄 Documentos")
    uploaded_file = st.file_uploader(
        "Adjunta permiso de circulación, V5C o ficha técnica",
        type=["jpg","jpeg","png","webp","pdf"],
        help="El asistente extraerá automáticamente marca, modelo, motor y año",
        label_visibility="collapsed",
    )
    if uploaded_file:
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            st.warning("⚠️ PDF: convierte a imagen para análisis visual")
        else:
            st.success(f"✅ {uploaded_file.name}")

    st.divider()
    if st.button("🗑️ Nueva consulta", use_container_width=True):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("# Selector de Kits")
    st.caption("OLIVA TORRAS Mount & Drive Kits · v8 BD · v10 Prompt · claude-sonnet-4-5")
with col2:
    brand  = st.session_state.brand
    kit    = st.session_state.kit_type
    if brand and kit:
        st.markdown(f"<div class='cost-indicator'>~$0.01/consulta</div>", unsafe_allow_html=True)

# ── Phase bar ─────────────────────────────────────────────────────────────────
phase = st.session_state.phase
p1 = "done" if phase > 1 else ("active" if phase == 1 else "")
p2 = "done" if phase > 2 else ("active" if phase == 2 else "")
p3 = "active" if phase == 3 else ""
st.markdown(f"""
<div class="phase-bar">
  <div class="phase-item {p1}">1 · Marca</div>
  <div class="phase-item {p2}">2 · Tipo de Kit</div>
  <div class="phase-item {p3}">3 · Consulta</div>
</div>
""", unsafe_allow_html=True)

# ── Welcome message ───────────────────────────────────────────────────────────
KIT_DESCRIPTIONS = {
    "Kit compresor A/C":            "KB — Compresor de aire acondicionado de cabina",
    "Kit compresor frío industrial": "KC — Compresor de frío para transporte refrigerado",
    "Kit alternador":               "KA — Alternador auxiliar",
    "Kit bomba hidráulica":         "KH — Bomba hidráulica",
    "Kit generador":                "KG — Generador eléctrico",
    "Kit chasis":                   "KF — Adaptación de chasis",
}

if not st.session_state.messages:
    with st.chat_message("assistant"):
        if not brand:
            st.markdown("""**Bienvenido al Selector de Kits OLIVA TORRAS.**

Selecciona la **marca del vehículo** en el panel izquierdo para empezar.

También puedes adjuntar el **permiso de circulación** o la **ficha técnica** y el asistente extraerá los datos automáticamente.""")
        elif not kit:
            kits = get_kit_types_for_brand(brand)
            desc = "\n".join(f"- **{KIT_DESCRIPTIONS.get(k, k)}**" for k in kits)
            st.markdown(f"""**Marca seleccionada: {brand}** ✓

Ahora selecciona el **tipo de kit** que necesitas:

{desc}

O escríbeme directamente qué necesitas.""")
        else:
            st.markdown(f"""**{brand} · {kit}** — Base de datos cargada ✓

Dime el **modelo**, **motor**, **año** y cualquier característica especial del vehículo.

Puedes adjuntar el **permiso de circulación** para que extraiga los datos automáticamente.""")

else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            if isinstance(content, str):
                st.markdown(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            st.markdown(block["text"])
                        elif block.get("type") == "image":
                            st.markdown('<div class="doc-badge">📄 Documento adjunto analizado</div>',
                                        unsafe_allow_html=True)

# ── Chat input ────────────────────────────────────────────────────────────────
placeholder = {
    1: "Selecciona una marca en el panel izquierdo…",
    2: "Selecciona el tipo de kit…",
    3: "Describe el vehículo o escribe tu consulta…",
}.get(phase, "Escribe tu consulta…")

user_input = st.chat_input(placeholder)

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)

    brand    = st.session_state.brand
    kit_type = st.session_state.kit_type

    if uploaded_file is not None and uploaded_file.name.rsplit(".",1)[-1].lower() != "pdf":
        image_bytes = uploaded_file.read()
        ext         = uploaded_file.name.rsplit(".", 1)[-1].lower()
        media_map   = {"jpg":"image/jpeg","jpeg":"image/jpeg",
                       "png":"image/png","webp":"image/webp"}
        media_type  = media_map.get(ext, "image/jpeg")

        # Añadir al historial con indicador visual
        st.session_state.messages.append({
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "indicator"}},
                {"type": "text",  "text": user_input}
            ]
        })
        # Para la API, construir el mensaje real
        api_messages = [
            m if m["role"] == "assistant" or isinstance(m["content"], str)
            else {"role": "user", "content": user_input}
            for m in st.session_state.messages[:-1]
        ] + [{"role": "user", "content": user_input}]

        with st.spinner("Analizando documento y buscando kit…"):
            reply = chat_with_image(
                messages=api_messages,
                image_data=image_bytes,
                media_type=media_type,
                brand=brand,
                kit_type=kit_type,
            )
    else:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.spinner("Buscando el kit…"):
            reply = chat(
                messages=st.session_state.messages,
                brand=brand,
                kit_type=kit_type,
            )

        # Auto-detectar marca/kit del contexto si no están seleccionados
        if not brand and any(b.lower() in reply.lower() for b in available_brands):
            for b in available_brands:
                if b.lower() in reply.lower():
                    st.session_state.brand = b
                    break

    with st.chat_message("assistant"):
        st.markdown(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
