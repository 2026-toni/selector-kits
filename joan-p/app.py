"""
app.py — Selector de Kits OLIVA TORRAS
Claude gestiona todo el flujo de selección según prompt v7.
Python (selector.py) solo prefiltra candidatos de la BD.
"""
import streamlit as st
import os, json, base64
from anthropic import Anthropic
from selector import (
    filter_candidates, candidates_to_json,
    detect_kit_type, detect_brand, get_models,
    get_model_max_year, get_kit_types, get_brands
)

BASE = os.path.dirname(os.path.abspath(__file__))

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Joan P. · Selector de Kits",
    page_icon="🔧",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap');
html,body,[class*="css"]{font-family:'Barlow',sans-serif;background:#f4f6f9}
.main>div{padding-top:0!important}
.ot-name{font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:700;color:#1a1a2e}
.ot-sub{font-size:11px;color:#1B6FC8;font-weight:600;letter-spacing:.05em;text-transform:uppercase}
.ot-dot{width:8px;height:8px;background:#22c55e;border-radius:50%;box-shadow:0 0 6px #22c55e;display:inline-block}
.bubble-u{background:linear-gradient(135deg,#1B6FC8,#0A3F7A);color:white;padding:10px 16px;border-radius:18px 18px 4px 18px;display:inline-block;max-width:75%;font-size:14px;line-height:1.5}
.bubble-a{background:white;color:#1a1a2e;padding:12px 16px;border-radius:4px 18px 18px 18px;display:inline-block;max-width:85%;font-size:14px;line-height:1.65;border:1px solid #e8edf5;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.msg-u{text-align:right;margin:6px 0}
.msg-a{text-align:left;margin:6px 0}
.stTextInput>div>div>input{border-radius:12px!important;border:1.5px solid #e2e8f0!important;font-family:'Barlow',sans-serif!important;font-size:14px!important}
.stTextInput>div>div>input:focus{border-color:#1B6FC8!important;box-shadow:0 0 0 3px rgba(27,111,200,.1)!important}
.stButton>button{background:linear-gradient(135deg,#1B6FC8,#0A3F7A)!important;color:white!important;border:none!important;border-radius:10px!important;font-family:'Barlow',sans-serif!important;font-weight:600!important}
table{width:100%;border-collapse:collapse;margin:8px 0;font-size:13px}
th{background:#f1f5f9;padding:7px 10px;text-align:left;border:1px solid #e2e8f0;font-weight:600;color:#475569;font-size:11px;text-transform:uppercase}
td{padding:6px 10px;border:1px solid #e2e8f0;color:#1a1a2e}
tr:nth-child(even) td{background:#f8fafc}
.kit-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.kit-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;font-size:13px}
.kit-name{font-weight:600;color:#1B6FC8;font-size:12px}
.kit-desc{color:#64748b;font-size:11px}
</style>
""", unsafe_allow_html=True)

# ── LOAD PROMPT ────────────────────────────────────────────────────────────────
@st.cache_resource
def load_prompt():
    candidates = [
        os.path.join(BASE, "prompt_selector_kits_v7.md"),
        os.path.join(os.getcwd(), "prompt_selector_kits_v7.md"),
        os.path.join(os.getcwd(), "joan-p", "prompt_selector_kits_v7.md"),
        "/mount/src/selector-kits/joan-p/prompt_selector_kits_v7.md",
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if path is None:
        raise FileNotFoundError(f"No se encontró prompt_selector_kits_v7.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# ── CLAUDE CLIENT ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY', '')
    return Anthropic(api_key=api_key)

# ── SYSTEM PROMPT BUILDER ──────────────────────────────────────────────────────
def build_system_prompt(candidates_json: str, context: dict) -> str:
    """
    Build the full system prompt with:
    1. The selector prompt v7
    2. The pre-filtered candidates from BD
    3. Context about available brands/models for current state
    """
    base_prompt = load_prompt()

    candidates_section = f"""
---

## CANDIDATOS ACTUALES (BD PREFILTRADA)

Los siguientes registros son los candidatos de la BD después del prefiltrado Python.
USA EXCLUSIVAMENTE ESTOS DATOS para seleccionar el kit. No inventes ningún dato.

Candidatos actuales ({context.get('total_candidates', 0)} filas, {context.get('unique_codes', 0)} códigos únicos):

```json
{candidates_json}
```

---

## CONTEXTO DEL ESTADO ACTUAL

- Kit type detectado: {context.get('kit_type', 'no detectado')}
- Marca detectada: {context.get('brand', 'no detectada')}
- Modelo detectado: {context.get('model', 'no detectado')}
- Modelos disponibles para esta marca+kit: {context.get('models_available', [])}

---
"""
    return base_prompt + candidates_section


# ── SESSION STATE ──────────────────────────────────────────────────────────────
def init_state():
    if 'messages' not in st.session_state:
        st.session_state.messages = []  # List of {role, content, image?}
    if 'sel_context' not in st.session_state:
        # Tracks what Python has detected to prefilter BD
        st.session_state.sel_context = {
            'kit_type': None,
            'brand': None,
            'model': None,
        }
    if 'candidates_json' not in st.session_state:
        st.session_state.candidates_json = '[]'
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False

init_state()


# ── UPDATE CONTEXT FROM MESSAGE ────────────────────────────────────────────────
def update_context(text: str):
    """
    Update sel_context based on user message.
    Detects kit_type, brand, model to prefilter BD.
    """
    ctx = st.session_state.sel_context

    if not ctx['kit_type']:
        kt = detect_kit_type(text)
        if kt:
            ctx['kit_type'] = kt

    if not ctx['brand']:
        brand = detect_brand(text)
        if brand:
            ctx['brand'] = brand

    if ctx['kit_type'] and ctx['brand'] and not ctx['model']:
        models = get_models(ctx['kit_type'], ctx['brand'])
        for m in sorted(models, key=lambda x: -len(x)):
            import re
            pat = re.escape(m).replace(r'\.', r'\.?').replace(r'\ ', r'\s*')
            if re.search(pat, text, re.I):
                ctx['model'] = m
                break

    st.session_state.sel_context = ctx


def refresh_candidates():
    """Prefilter BD based on current sel_context and update candidates_json."""
    ctx = st.session_state.sel_context
    records = filter_candidates(
        kit_type=ctx.get('kit_type'),
        brand=ctx.get('brand'),
        model=ctx.get('model'),
        max_rows=400
    )
    import pandas as pd
    # Get unique codes count
    unique_codes = len(set(r.get('code') for r in records if r.get('code')))

    ctx_info = {
        'kit_type': ctx.get('kit_type', 'no detectado'),
        'brand': ctx.get('brand', 'no detectada'),
        'model': ctx.get('model', 'no detectado'),
        'total_candidates': len(records),
        'unique_codes': unique_codes,
        'models_available': get_models(ctx.get('kit_type'), ctx.get('brand')) if ctx.get('kit_type') and ctx.get('brand') else [],
    }

    st.session_state.candidates_json = candidates_to_json(records)
    st.session_state.ctx_info = ctx_info


# ── CALL CLAUDE ────────────────────────────────────────────────────────────────
def call_claude(user_message: str, image_data: dict = None) -> str:
    """
    Send conversation to Claude with current candidates and get response.
    Claude manages the FULL selection logic according to prompt v7.
    """
    client = get_client()

    # Build system prompt with current candidates
    ctx_info = st.session_state.get('ctx_info', {
        'kit_type': 'no detectado', 'brand': 'no detectada',
        'model': 'no detectado', 'total_candidates': 0,
        'unique_codes': 0, 'models_available': []
    })
    system = build_system_prompt(st.session_state.candidates_json, ctx_info)

    # Build messages for API
    api_messages = []
    for msg in st.session_state.messages:
        if msg['role'] == 'user':
            if msg.get('image'):
                # Message with image
                api_messages.append({
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': msg['image']['media_type'],
                                'data': msg['image']['data'],
                            }
                        },
                        {'type': 'text', 'text': msg['content']}
                    ]
                })
            else:
                api_messages.append({'role': 'user', 'content': msg['content']})
        else:
            api_messages.append({'role': 'assistant', 'content': msg['content']})

    # Add current user message
    if image_data:
        api_messages.append({
            'role': 'user',
            'content': [
                {
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': image_data['media_type'],
                        'data': image_data['data'],
                    }
                },
                {'type': 'text', 'text': user_message}
            ]
        })
    else:
        api_messages.append({'role': 'user', 'content': user_message})

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system=system,
        messages=api_messages
    )

    return response.content[0].text


# ── HEADER ─────────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    logo_path = os.path.join(BASE, "logo.jpg")
    if os.path.exists(logo_path):
        st.image(logo_path, width=200)
with c2:
    st.markdown(
        '<div class="ot-name">Joan P.</div>'
        '<div class="ot-sub">Kit Selector · OT M&DK</div>',
        unsafe_allow_html=True
    )
with c3:
    st.markdown(
        '<div style="text-align:right;padding-top:8px">'
        '<span class="ot-dot"></span> '
        '<span style="font-size:12px;color:#555">En línea</span>'
        '</div>',
        unsafe_allow_html=True
    )
st.divider()

# ── WELCOME CARD (only on first load) ─────────────────────────────────────────
if not st.session_state.initialized:
    st.markdown("""
    <div style="background:white;border:1px solid #e8edf5;border-radius:16px;
                padding:20px 24px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.04)">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:20px;
                    font-weight:700;color:#1a1a2e">👋 Hola, soy Joan P.</div>
        <div style="font-size:13px;color:#64748b;margin-bottom:12px">
            Asistente de selección de kits · OLIVA TORRAS Mount &amp; Drive Kits
        </div>
        <div style="font-size:14px;color:#374151">
            Te ayudaré a encontrar el kit exacto con las mínimas preguntas.<br><br>
            <b>¿Qué tipo de kit necesitas?</b>
        </div>
        <div class="kit-grid">
            <div class="kit-card">
                <div style="font-size:18px">🧊</div>
                <div class="kit-name">KB — Compresor A/C</div>
                <div class="kit-desc">Aire acondicionado de cabina</div>
            </div>
            <div class="kit-card">
                <div style="font-size:18px">❄️</div>
                <div class="kit-name">KC — Frío industrial</div>
                <div class="kit-desc">Compresor frío de transporte</div>
            </div>
            <div class="kit-card">
                <div style="font-size:18px">⚡</div>
                <div class="kit-name">KA — Alternador</div>
                <div class="kit-desc">Alternador auxiliar</div>
            </div>
            <div class="kit-card">
                <div style="font-size:18px">💧</div>
                <div class="kit-name">KH — Bomba hidráulica</div>
                <div class="kit-desc">Bomba hidráulica auxiliar</div>
            </div>
            <div class="kit-card">
                <div style="font-size:18px">🔌</div>
                <div class="kit-name">KG — Generador</div>
                <div class="kit-desc">Generador eléctrico</div>
            </div>
            <div class="kit-card">
                <div style="font-size:18px">🏗️</div>
                <div class="kit-name">KF — Chasis</div>
                <div class="kit-desc">Adaptación de chasis</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── CHAT DISPLAY ───────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg['role'] == 'user':
        display_text = msg['content']
        if msg.get('image'):
            display_text = f"📎 [imagen adjunta] {display_text}" if display_text else "📎 [imagen adjunta]"
        st.markdown(
            f'<div class="msg-u"><div class="bubble-u">{display_text}</div></div>',
            unsafe_allow_html=True
        )
    else:
        # Render markdown inside bubble
        import re as _re
        content = msg['content']
        st.markdown(
            f'<div class="msg-a"><div class="bubble-a">{content}</div></div>',
            unsafe_allow_html=True
        )

st.divider()

# ── INPUT FORM ─────────────────────────────────────────────────────────────────
with st.form(key='chat_form', clear_on_submit=True):
    col_input, col_file, col_send, col_reset = st.columns([5, 1, 1, 1])

    with col_input:
        user_input = st.text_input(
            "",
            placeholder="Escribe aquí... (marca, modelo, tipo de kit...)",
            label_visibility="collapsed"
        )
    with col_file:
        uploaded_file = st.file_uploader(
            "📎",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed"
        )
    with col_send:
        send = st.form_submit_button("➤")
    with col_reset:
        reset = st.form_submit_button("↺")

# ── RESET ──────────────────────────────────────────────────────────────────────
if reset:
    st.session_state.messages = []
    st.session_state.sel_context = {'kit_type': None, 'brand': None, 'model': None}
    st.session_state.candidates_json = '[]'
    st.session_state.initialized = False
    st.rerun()

# ── SEND ───────────────────────────────────────────────────────────────────────
if send and (user_input.strip() or uploaded_file):
    msg_text = user_input.strip() if user_input else ""
    image_data = None

    # Process image if uploaded
    if uploaded_file:
        img_bytes = uploaded_file.read()
        img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
        media_type = uploaded_file.type or "image/jpeg"
        image_data = {'media_type': media_type, 'data': img_b64}
        if not msg_text:
            msg_text = "Adjunto ficha técnica del vehículo."

    # Update context from user message
    update_context(msg_text)
    refresh_candidates()

    # Store user message
    user_msg = {'role': 'user', 'content': msg_text}
    if image_data:
        user_msg['image'] = image_data
    st.session_state.messages.append(user_msg)

    # Call Claude — he manages ALL the selection logic
    with st.spinner("Joan P. está pensando..."):
        response = call_claude(msg_text, image_data)

    # Update context from Claude's response (extract kit/brand/model if mentioned)
    update_context(response)
    refresh_candidates()

    # Store assistant response
    st.session_state.messages.append({'role': 'assistant', 'content': response})

    # Mark as initialized after first exchange
    st.session_state.initialized = True

    st.rerun()
