import streamlit as st
import os
import re
import json
from anthropic import Anthropic
from selector import (
    apply_filters, apply_awd_filter, next_step,
    process_answer, get_final_result, get_unique_codes,
    get_unique_values, DB
)

BASE = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="Joan P. · Selector de Kits", page_icon="🔧", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap');
html,body,[class*="css"]{font-family:'Barlow',sans-serif;background:#f4f6f9}
.main>div{padding-top:0!important}
.ot-dot{width:8px;height:8px;background:#22c55e;border-radius:50%;box-shadow:0 0 6px #22c55e;display:inline-block}
.ot-name{font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:700;color:#1a1a2e}
.ot-sub{font-size:11px;color:#1B6FC8;font-weight:600;letter-spacing:.05em;text-transform:uppercase}
.bubble-u{background:linear-gradient(135deg,#1B6FC8,#0A3F7A);color:white;padding:10px 16px;border-radius:18px 18px 4px 18px;display:inline-block;max-width:75%;font-size:14px;line-height:1.5;box-shadow:0 2px 8px rgba(27,111,200,.25)}
.bubble-a{background:white;color:#1a1a2e;padding:12px 16px;border-radius:4px 18px 18px 18px;display:inline-block;max-width:82%;font-size:14px;line-height:1.65;border:1px solid #e8edf5;box-shadow:0 2px 8px rgba(0,0,0,.05)}
.msg-u{text-align:right;margin:6px 0}.msg-a{text-align:left;margin:6px 0}
.kit-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.kit-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;font-size:13px}
.kit-name{font-weight:600;color:#1B6FC8;font-size:12px}.kit-desc{color:#64748b;font-size:11px}
.wbox{background:white;border:1px solid #e8edf5;border-radius:16px;padding:20px 24px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.04)}
.result-box{background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1px solid #86efac;border-radius:12px;padding:16px;margin:10px 0}
.stTextInput>div>div>input{border-radius:12px!important;border:1.5px solid #e2e8f0!important;font-family:'Barlow',sans-serif!important;font-size:14px!important}
.stTextInput>div>div>input:focus{border-color:#1B6FC8!important;box-shadow:0 0 0 3px rgba(27,111,200,.1)!important}
.stButton>button{background:linear-gradient(135deg,#1B6FC8,#0A3F7A)!important;color:white!important;border:none!important;border-radius:10px!important;font-family:'Barlow',sans-serif!important;font-weight:600!important}
table{width:100%;border-collapse:collapse;margin:8px 0;font-size:13px}
th{background:#f1f5f9;padding:7px 10px;text-align:left;border:1px solid #e2e8f0;font-weight:600;color:#475569;font-size:11px;text-transform:uppercase}
td{padding:6px 10px;border:1px solid #e2e8f0;color:#1a1a2e}
tr:nth-child(even) td{background:#f8fafc}
</style>
""", unsafe_allow_html=True)

SYSTEM_PROMPT_FINAL = """Eres Joan P., asistente de selección de kits de OLIVA TORRAS Mount & Drive Kits.
Se te proporciona el resultado final de una selección hecha por un motor Python. 
Tu tarea es redactar la respuesta final de forma clara y comercial.

Formato de respuesta:
✅ **Referencia seleccionada: [CODE]**
Motivo: [modelo] · [motor + cilindrada] · [desde año] · [componente] · [diferencial si aplica]

📋 **Notas importantes:** (muestra TODO el noteeng — no omitas nada)

🔧 **Embrague:**
- Si embrague_esp vacío y tipus=N: "⚠️ Previsto para embrague estándar `[embrague_std]` — no incluido en el kit."
- Si embrague_esp = embrague_std: "✓ Incluye embrague estándar `[embrague_std]`." + si tipus N-E → "Disponible también: **[CODE]E**" + si N-S → "**[CODE]S**"
- Si embrague_esp ≠ embrague_std: "✓ Embrague estándar: `[embrague_std]`." + versión E/S según tipus

Sé conciso pero completo. No inventes datos."""

SYSTEM_PROMPT_COMPARE = """Eres Joan P. de OLIVA TORRAS Mount & Drive Kits.
Se te dan varios códigos candidatos con sus datos. Muestra una tabla comparativa clara y haz la siguiente pregunta mínima necesaria para reducirlos a 1.
No inventes datos. Sé conciso."""

@st.cache_resource
def get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY', '')
    return Anthropic(api_key=api_key)

def init_state():
    if 'sel_state' not in st.session_state:
        st.session_state.sel_state = {}
    if 'chat' not in st.session_state:
        st.session_state.chat = []  # list of (role, text)
    if 'step_type' not in st.session_state:
        st.session_state.step_type = None
    if 'done' not in st.session_state:
        st.session_state.done = False

def add_msg(role, text):
    st.session_state.chat.append((role, text))

def format_bot_welcome():
    return """**¡Hola! Soy Joan P.** 👋

Asistente de selección de kits · OLIVA TORRAS Mount & Drive Kits

Te ayudaré a encontrar el kit exacto con las mínimas preguntas.

**¿Qué tipo de kit necesitas?**

| Prefijo | Tipo | Descripción |
|---|---|---|
| KB | Compresor A/C | Aire acondicionado de cabina |
| KC | Frío industrial | Compresor de frío de transporte |
| KA | Alternador | Alternador auxiliar |
| KH | Bomba hidráulica | Bomba hidráulica auxiliar |
| KG | Generador | Generador eléctrico |
| KF | Chasis | Adaptación de chasis |"""

def run_step():
    """Execute current step and get next question."""
    state = st.session_state.sel_state
    data = apply_filters(state)
    data = apply_awd_filter(data, state)

    step_type, question, options, is_done = next_step(state, data)
    st.session_state.step_type = step_type
    st.session_state.done = is_done

    if is_done:
        if step_type == 'done':
            # Format final result
            result = get_final_result(options, data)
            client = get_client()
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                system=SYSTEM_PROMPT_FINAL,
                messages=[{'role': 'user', 'content': f"Resultado de selección:\n{json.dumps(result, ensure_ascii=False)}"}]
            )
            add_msg('bot', resp.content[0].text)
        else:
            add_msg('bot', "❌ No he encontrado ningún kit que cumpla todos los criterios indicados. Intenta con **↺ Nueva selección** y verifica los datos del vehículo.")
        return

    if step_type == 'compare':
        # Multiple candidates — ask Claude to compare
        codes = options  # dict of code -> row
        detail = []
        for code, r in list(codes.items())[:10]:
            detail.append({
                'code': code,
                'model': r.get('model_clean'),
                'engine': r.get('engine_all') or r.get('engine_clean'),
                'cilinder': r.get('cilinder'),
                'year_from': r.get('year_from_v4'),
                'year_to': r.get('year_to_v4'),
                'components': get_unique_values(data, 'nom_opcio_compressor'),
                'flag_auto_tensioner': r.get('flag_auto_tensioner'),
                'flag_n63_full_option': r.get('flag_n63_full_option'),
                'flag_n63_pulley_yes': r.get('flag_n63_pulley_yes'),
                'flag_n63_pulley_no': r.get('flag_n63_pulley_no'),
                'flag_pfmot_yes': r.get('flag_pfmot_yes'),
                'flag_pfmot_no': r.get('flag_pfmot_no'),
                'flag_sanden': r.get('flag_sanden'),
                'flag_gearbox_v3': r.get('flag_gearbox_v3'),
                'flag_man_option': r.get('flag_man_option'),
                'ac_filter': r.get('ac_filter'),
            })
        client = get_client()
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=SYSTEM_PROMPT_COMPARE,
            messages=[{'role': 'user', 'content': f"Candidatos:\n{json.dumps(detail, ensure_ascii=False)}\n\nHaz tabla comparativa y pregunta lo mínimo para llegar a 1 código."}]
        )
        add_msg('bot', resp.content[0].text)
        st.session_state.step_type = 'compare_free'
        return

    # Format question with options
    msg = question + '\n\n'
    if isinstance(options, list):
        if options and isinstance(options[0], tuple):
            # Engine options with cilinder
            for eng, cil in options:
                cil_str = f" · {cil}" if cil else ""
                msg += f"- **{eng}**{cil_str}\n"
        elif options and isinstance(options[0], tuple) and len(options[0]) == 3:
            # Kit type options
            for code, name, desc in options:
                msg += f"- **{code}** — {name}: {desc}\n"
        else:
            for opt in options:
                msg += f"- {opt}\n"
    elif isinstance(options, dict):
        # Grouped components
        for group, comps in options.items():
            msg += f"\n**{group}**\n"
            for c in comps:
                msg += f"  · {c}\n"

    add_msg('bot', msg)

def handle_input(user_text):
    """Process user input and advance state."""
    add_msg('user', user_text)
    state = st.session_state.sel_state
    step_type = st.session_state.step_type

    if step_type == 'compare_free':
        # Free text comparison — Claude handles
        # Try to extract state from answer
        data = apply_filters(state)
        data = apply_awd_filter(data, state)
        codes = get_unique_codes(data)

        # Try to detect if user picked a specific code
        for code in codes:
            if code.upper() in user_text.upper():
                # User selected a specific code
                st.session_state.sel_state['_selected_code'] = code
                result = get_final_result(codes[code], data)
                client = get_client()
                resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=800,
                    system=SYSTEM_PROMPT_FINAL,
                    messages=[{'role': 'user', 'content': f"Resultado:\n{json.dumps(result, ensure_ascii=False)}"}]
                )
                add_msg('bot', resp.content[0].text)
                st.session_state.done = True
                return

        # Otherwise let the selector figure out a filter
        new_state = process_answer(state, 'compare', user_text, data)
        st.session_state.sel_state = new_state
    else:
        data = apply_filters(state)
        data = apply_awd_filter(data, state)
        new_state = process_answer(state, step_type, user_text, data)
        st.session_state.sel_state = new_state

    if not st.session_state.done:
        run_step()

# ── MAIN UI ───────────────────────────────────────────────────────────────────
init_state()

# Header
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    st.image(os.path.join(BASE, "logo.jpg"), width=200)
with c2:
    st.markdown('<div class="ot-name">Joan P.</div><div class="ot-sub">Kit Selector · OT M&DK</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div style="text-align:right;padding-top:8px"><span class="ot-dot"></span> <span style="font-size:12px;color:#555">En línea</span></div>', unsafe_allow_html=True)

st.divider()

# Initialize chat with welcome
if not st.session_state.chat:
    add_msg('bot', format_bot_welcome())
    run_step()

# Display chat
for role, text in st.session_state.chat:
    if role == 'user':
        st.markdown(f'<div class="msg-u"><div class="bubble-u">{text}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="msg-a"><div class="bubble-a">{text}</div></div>', unsafe_allow_html=True)

st.divider()

# Input
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
    st.session_state.step_type = None
    st.session_state.done = False
    st.rerun()

if send and user_input and user_input.strip():
    handle_input(user_input.strip())
    st.rerun()
