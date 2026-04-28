import streamlit as st
import os, json, re
from anthropic import Anthropic
from selector import apply_filters, get_codes, next_question, apply_answer, DB

BASE = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="Joan P. · Selector de Kits", page_icon="🔧", layout="centered")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap');
html,body,[class*="css"]{font-family:'Barlow',sans-serif;background:#f4f6f9}
.main>div{padding-top:0!important}
.ot-name{font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:700;color:#1a1a2e}
.ot-sub{font-size:11px;color:#1B6FC8;font-weight:600;letter-spacing:.05em;text-transform:uppercase}
.ot-dot{width:8px;height:8px;background:#22c55e;border-radius:50%;box-shadow:0 0 6px #22c55e;display:inline-block}
.bubble-u{background:linear-gradient(135deg,#1B6FC8,#0A3F7A);color:white;padding:10px 16px;border-radius:18px 18px 4px 18px;display:inline-block;max-width:75%;font-size:14px;line-height:1.5}
.bubble-a{background:white;color:#1a1a2e;padding:12px 16px;border-radius:4px 18px 18px 18px;display:inline-block;max-width:82%;font-size:14px;line-height:1.65;border:1px solid #e8edf5;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.msg-u{text-align:right;margin:6px 0}.msg-a{text-align:left;margin:6px 0}
.kit-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.kit-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;font-size:13px}
.kit-name{font-weight:600;color:#1B6FC8;font-size:12px}.kit-desc{color:#64748b;font-size:11px}
.stTextInput>div>div>input{border-radius:12px!important;border:1.5px solid #e2e8f0!important;font-family:'Barlow',sans-serif!important;font-size:14px!important}
.stTextInput>div>div>input:focus{border-color:#1B6FC8!important;box-shadow:0 0 0 3px rgba(27,111,200,.1)!important}
.stButton>button{background:linear-gradient(135deg,#1B6FC8,#0A3F7A)!important;color:white!important;border:none!important;border-radius:10px!important;font-family:'Barlow',sans-serif!important;font-weight:600!important}
table{width:100%;border-collapse:collapse;margin:8px 0;font-size:13px}
th{background:#f1f5f9;padding:7px 10px;text-align:left;border:1px solid #e2e8f0;font-weight:600;color:#475569;font-size:11px;text-transform:uppercase}
td{padding:6px 10px;border:1px solid #e2e8f0;color:#1a1a2e}
tr:nth-child(even) td{background:#f8fafc}
</style>
""", unsafe_allow_html=True)

# ── CLAUDE CLIENT ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY', '')
    return Anthropic(api_key=api_key)

# ── FORMAT QUESTION ───────────────────────────────────────────────────────────
def format_question(result):
    """Format the next_question result into a readable message."""
    step = result['step']
    question = result['question']
    options = result['options']
    total = result['total']

    msg = f"*{total} candidatos disponibles*\n\n{question}\n\n"

    if isinstance(options, list):
        for opt in options:
            msg += f"- {opt}\n"
    elif isinstance(options, dict):
        for group, items in options.items():
            msg += f"\n**{group}**\n"
            for item in items:
                msg += f"  · {item}\n"

    return msg

def format_final(result):
    """Format the final selection result."""
    candidate = result['result']
    if not candidate:
        return "❌ No se encontró ningún kit. Intenta de nuevo con ↺"

    code = candidate.get('code','')
    model = candidate.get('model','')
    engine = candidate.get('engine','')
    cil = candidate.get('cilinder','')
    year_from = candidate.get('year_from_v4','')
    components = candidate.get('components',[])
    noteeng = candidate.get('noteeng','') or ''
    noteeng = noteeng.replace('_x000D_','').replace('\r','').strip()
    emb_std = (candidate.get('embrague_std') or '').replace('\\n',' · ')
    emb_esp = (candidate.get('embrague_esp') or '').replace('\\n',' · ')
    tipus = candidate.get('tipus_embrague','') or ''
    engine_str = f"{engine} ({cil}cc)" if cil else engine
    comp_str = components[0] if components else ''

    msg = f"✅ **Referencia seleccionada: {code}**\n"
    msg += f"Motivo: {model} · {engine_str} · desde {year_from} · {comp_str}\n\n"

    if noteeng:
        msg += f"📋 **Notas importantes:**\n"
        for line in noteeng.split('\n'):
            line = line.strip().lstrip('- ')
            if line:
                msg += f"· {line}\n"
        msg += "\n"

    # Embrague logic
    msg += "🔧 **Embrague:**\n"
    if not emb_esp and tipus in ('N', ''):
        msg += f"⚠️ Previsto para embrague estándar `{emb_std}` — no incluido en el kit.\n"
    elif emb_esp == emb_std:
        msg += f"✓ Incluye embrague estándar `{emb_std}`.\n"
        if 'E' in tipus and tipus != 'N':
            msg += f"· Disponible también con embrague especial: **{code}E** · `{emb_esp}`\n"
        if 'S' in tipus and tipus != 'N':
            msg += f"· Disponible también para SANDEN: **{code}S** · `{emb_esp}`\n"
    else:
        if emb_std:
            msg += f"✓ Embrague estándar incluido: `{emb_std}`\n"
        if 'E' in tipus and emb_esp:
            msg += f"· Versión especial disponible: **{code}E** · `{emb_esp}`\n"
        if 'S' in tipus and emb_esp:
            msg += f"· Versión SANDEN disponible: **{code}S** · `{emb_esp}`\n"

    return msg

# ── SESSION STATE ──────────────────────────────────────────────────────────────
if 'sel_state' not in st.session_state:
    st.session_state.sel_state = {}
if 'chat' not in st.session_state:
    st.session_state.chat = []  # (role, text)
if 'current_step' not in st.session_state:
    st.session_state.current_step = None
if 'done' not in st.session_state:
    st.session_state.done = False

def add_bot(text):
    st.session_state.chat.append(('bot', text))

def add_user(text):
    st.session_state.chat.append(('user', text))

def advance():
    """Run next_question and add result to chat."""
    result = next_question(st.session_state.sel_state)
    st.session_state.current_step = result['step']

    if result['done']:
        st.session_state.done = True
        add_bot(format_final(result))
    else:
        add_bot(format_question(result))

# ── HEADER ─────────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    st.image(os.path.join(BASE, "logo.jpg"), width=200)
with c2:
    st.markdown('<div class="ot-name">Joan P.</div><div class="ot-sub">Kit Selector · OT M&DK</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div style="text-align:right;padding-top:8px"><span class="ot-dot"></span> <span style="font-size:12px;color:#555">En línea</span></div>', unsafe_allow_html=True)
st.divider()

# ── INIT ───────────────────────────────────────────────────────────────────────
if not st.session_state.chat:
    st.markdown("""<div style="background:white;border:1px solid #e8edf5;border-radius:16px;padding:20px 24px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.04)">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:700;color:#1a1a2e">👋 Hola, soy Joan P.</div>
    <div style="font-size:13px;color:#64748b;margin-bottom:12px">Asistente de selección de kits · OLIVA TORRAS Mount & Drive Kits</div>
    <div style="font-size:14px;color:#374151">Te ayudaré a encontrar el kit exacto con las mínimas preguntas.<br><br><b>¿Qué tipo de kit necesitas?</b></div>
    <div class="kit-grid">
    <div class="kit-card"><div style="font-size:18px">🧊</div><div class="kit-name">KB — Compresor A/C</div><div class="kit-desc">Aire acondicionado de cabina</div></div>
    <div class="kit-card"><div style="font-size:18px">❄️</div><div class="kit-name">KC — Frío industrial</div><div class="kit-desc">Compresor frío de transporte</div></div>
    <div class="kit-card"><div style="font-size:18px">⚡</div><div class="kit-name">KA — Alternador</div><div class="kit-desc">Alternador auxiliar</div></div>
    <div class="kit-card"><div style="font-size:18px">💧</div><div class="kit-name">KH — Bomba hidráulica</div><div class="kit-desc">Bomba hidráulica auxiliar</div></div>
    <div class="kit-card"><div style="font-size:18px">🔌</div><div class="kit-name">KG — Generador</div><div class="kit-desc">Generador eléctrico</div></div>
    <div class="kit-card"><div style="font-size:18px">🏗️</div><div class="kit-name">KF — Chasis</div><div class="kit-desc">Adaptación de chasis</div></div>
    </div></div>""", unsafe_allow_html=True)
    advance()

# ── CHAT DISPLAY ───────────────────────────────────────────────────────────────
for role, text in st.session_state.chat:
    if role == 'user':
        st.markdown(f'<div class="msg-u"><div class="bubble-u">{text}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="msg-a"><div class="bubble-a">{text}</div></div>', unsafe_allow_html=True)

st.divider()

# ── INPUT ──────────────────────────────────────────────────────────────────────
with st.form(key='chat_form', clear_on_submit=True):
    ci, cb, cn = st.columns([6, 1, 1])
    with ci:
        user_input = st.text_input("", placeholder="Escribe aquí...", label_visibility="collapsed",
                                   disabled=st.session_state.done)
    with cb:
        send = st.form_submit_button("➤", disabled=st.session_state.done)
    with cn:
        new_s = st.form_submit_button("↺")

if new_s:
    st.session_state.sel_state = {}
    st.session_state.chat = []
    st.session_state.current_step = None
    st.session_state.done = False
    st.rerun()

if send and user_input and user_input.strip():
    msg = user_input.strip()
    add_user(msg)

    # Python processes the answer and advances state
    step = st.session_state.current_step
    new_state = apply_answer(st.session_state.sel_state, step, msg)
    st.session_state.sel_state = new_state

    # Python decides next question
    advance()
    st.rerun()
