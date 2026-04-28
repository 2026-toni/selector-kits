import streamlit as st
import os, json, re
from anthropic import Anthropic
from selector import (apply_filters, apply_awd_filter, get_unique_codes,
                      get_unique_values, normalize_comp, detect_brand,
                      detect_model, detect_year, DB)

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

SYSTEM_PROMPT = """Eres Joan P., asistente comercial experto en selección de kits de OLIVA TORRAS Mount & Drive Kits.

Se te proporciona en cada mensaje:
1. El historial de conversación
2. [DATOS BD]: los candidatos filtrados por Python — ESTA ES LA ÚNICA FUENTE DE VERDAD

ESTILO: texto natural. Sin ## ni "PASO X". Conciso (3-4 líneas máximo salvo tablas). Una pregunta por turno. Confirma con "✓ [dato]".

FLUJO OBLIGATORIO — sigue este orden exacto, detente al llegar a 1 código:

1. TIPO DE KIT: KB=A/C · KC=frío industrial · KA=alternador · KH=bomba · KG=generador · KF=chasis
2. MARCA · 3. MODELO (4-8 opciones de available_models) · 4. TRACCIÓN (si has_rwd Y has_fwd)
5. ¿VEHÍCULO NUEVO? SÍ=vigentes · NO=pide año
6. AÑO (si no nuevo) · 7. MOTOR (usa available_engines con cilindrada)
8. COMPONENTE (agrupa por tipo, opciones de available_components)
9. FLAGS (solo si varían en los candidatos): tensor · pfmot · n63 · sanden · awd · gearbox · man_option
10. A/C (solo si ac_values tiene yes Y no)

SELECCIÓN FINAL (total_codes=1):
✅ **Referencia seleccionada: [CODE]**
Motivo: [model] · [engine + cilinder] · [desde year_from_v4] · [component] · [diferencial]
📋 **Notas importantes:** (TODO el noteeng, sin omitir nada)
🔧 **Embrague:** (según lógica embrague_esp/embrague_std/tipus_embrague)

REGLAS: Solo usa datos de [DATOS BD]. No inventes. Una pregunta por turno. Excluye STANDARD BRACKET."""

@st.cache_resource
def get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY', '')
    return Anthropic(api_key=api_key)

def extract_state(messages):
    """Extract filter state from all conversation messages using Python."""
    text = ' '.join(m.get('content','') for m in messages if isinstance(m.get('content'), str))
    s = {}

    # Kit type
    if re.search(r'compresor\s*a/c|\bkb\b', text, re.I): s['kit_type'] = 'Kit compresor A/C'
    elif re.search(r'fr[ií]o\s*industrial|\bkc\b', text, re.I): s['kit_type'] = 'Kit compresor frío industrial'
    elif re.search(r'alternador|\bka\b', text, re.I): s['kit_type'] = 'Kit alternador'
    elif re.search(r'bomba|\bkh\b', text, re.I): s['kit_type'] = 'Kit bomba hidráulica'
    elif re.search(r'generador|\bkg\b', text, re.I): s['kit_type'] = 'Kit generador'
    elif re.search(r'chasis|\bkf\b', text, re.I): s['kit_type'] = 'Kit chasis'

    # Brand
    brand = detect_brand(text)
    if brand: s['brand'] = brand

    # Model
    model = detect_model(text)
    if model: s['model_clean'] = model

    # Traction
    if re.search(r'\brwd\b|tracci[oó]n\s*trasera|rear\s*wheel', text, re.I): s['flag_rwd'] = True
    if re.search(r'\bfwd\b|tracci[oó]n\s*delantera|front\s*wheel', text, re.I): s['flag_fwd'] = True

    # New vehicle
    if re.search(r'\bsí\b.*nuevo|si\b.*nuevo|es\s*nuevo|matriculaci[oó]n\s*reciente|veh[ií]culo\s*nuevo', text, re.I):
        s['new_vehicle'] = True
    elif re.search(r'no.*nuevo|tengo\s*el\s*año|año\s*exacto', text, re.I):
        s['new_vehicle'] = False

    # Year
    if not s.get('new_vehicle'):
        yr = detect_year(text)
        if yr: s['year'] = yr

    # Component
    comp = normalize_comp(text)
    if comp: s['component'] = comp

    # Flags from conversation
    if re.search(r'tensor\s*autom[áa]tico|auto\s*tensor', text, re.I): s['flag_auto_tensioner'] = 1
    if re.search(r'tensor\s*est[áa]ndar|tensor\s*manual|tensor\s*normal', text, re.I): s['flag_auto_tensioner_no'] = True
    if re.search(r'con\s*bracket|bracket\s*original|opci[oó]n\s*n63\s*completa', text, re.I): s['n63_full'] = True
    if re.search(r'solo\s*la\s*polea|solo\s*polea|sin\s*bracket', text, re.I): s['n63_only'] = True
    if re.search(r'sin\s*polea|no\s*lleva\s*polea|no\s*tiene\s*polea', text, re.I): s['n63_none'] = True
    if re.search(r'con\s*pfmot|tiene\s*pfmot|con\s*pto|tiene\s*pto', text, re.I): s['flag_pfmot_yes'] = 1
    if re.search(r'sin\s*pfmot|no\s*pfmot|sin\s*pto|no\s*pto', text, re.I): s['flag_pfmot_no'] = 1
    if re.search(r'sanden|es\s*sanden|compresor\s*sanden', text, re.I): s['flag_sanden'] = 1
    if re.search(r'no\s*sanden|no\s*es\s*sanden', text, re.I): s['flag_sanden'] = 0
    if re.search(r'\bawd\b|4x4|tracci[oó]n\s*total|es\s*awd', text, re.I): s['is_awd'] = True
    if re.search(r'no\s*awd|no\s*4x4|no\s*es\s*awd', text, re.I): s['is_awd'] = False
    if re.search(r'con\s*a/c|tiene\s*a/c|s[ií]\s*a/c|a/c\s*de\s*f[áa]brica', text, re.I): s['ac_filter'] = 'yes'
    if re.search(r'sin\s*a/c|no\s*tiene\s*a/c|no\s*a/c', text, re.I): s['ac_filter'] = 'no'
    if re.search(r'caja\s*autom[áa]tica|cambios\s*autom[áa]ticos', text, re.I): s['flag_gearbox_ok'] = True
    if re.search(r'man\s*120ff|0p0gp', text, re.I): s['flag_man_option'] = 1

    return s

def get_db_context(state, all_messages):
    """Filter DB with Python and build context for Claude."""
    data = apply_filters(state)
    data = apply_awd_filter(data, state)

    by_code = {}
    for r in data:
        if r.get('code') and r['code'] not in by_code:
            by_code[r['code']] = r
    codes = list(by_code.values())
    uniq = lambda lst: list(dict.fromkeys(x for x in lst if x))

    ctx = {
        'total_codes': len(codes),
        'filters_active': state,
        'available_brands': uniq(r.get('brand') for r in codes),
        'available_models': uniq(r.get('model_clean') for r in codes),
        'available_engines': [
            {'engine': r.get('engine_all') or r.get('engine_clean'), 'cilinder': r.get('cilinder')}
            for r in codes
        ],
        'available_components': uniq(r.get('nom_opcio_compressor') for r in data),
        'has_rwd': any(r.get('flag_rwd') == 1 for r in codes),
        'has_fwd': any(r.get('flag_fwd') == 1 for r in codes),
        'ac_values': uniq(r.get('ac_filter') for r in codes),
        'flags': {
            'auto_tensioner_mixed': any(r.get('flag_auto_tensioner') == 1 for r in codes) and any(r.get('flag_auto_tensioner') != 1 for r in codes),
            'pfmot_mixed': any(r.get('flag_pfmot_yes') == 1 for r in codes) and any(r.get('flag_pfmot_no') == 1 for r in codes),
            'n63_variants': any(r.get('flag_n63_full_option') == 1 for r in codes) or (any(r.get('flag_n63_pulley_yes') == 1 for r in codes) and any(r.get('flag_n63_pulley_no') == 1 for r in codes)),
            'sanden_mixed': any(r.get('flag_sanden') == 1 for r in codes) and any(r.get('flag_sanden') != 1 for r in codes),
            'awd_mixed': any(r.get('flag_awd') == 1 for r in codes) and any(r.get('flag_awd') != 1 for r in codes),
            'gearbox_mixed': len(set(r.get('flag_gearbox_v3') for r in codes if r.get('flag_gearbox_v3'))) > 0,
            'man_option_mixed': any(r.get('flag_man_option') == 1 for r in codes) and any(r.get('flag_man_option') != 1 for r in codes),
        }
    }

    if len(codes) <= 12:
        ctx['candidates'] = []
        for r in codes:
            ctx['candidates'].append({
                'code': r.get('code'),
                'model': r.get('model_clean'),
                'engine': r.get('engine_all') or r.get('engine_clean'),
                'cilinder': r.get('cilinder'),
                'year_from_v4': r.get('year_from_v4'),
                'year_to_v4': r.get('year_to_v4'),
                'components': uniq(d.get('nom_opcio_compressor') for d in data if d.get('code') == r.get('code')),
                'flag_rwd': r.get('flag_rwd'), 'flag_fwd': r.get('flag_fwd'),
                'flag_awd': r.get('flag_awd'),
                'flag_auto_tensioner': r.get('flag_auto_tensioner'),
                'flag_n63_full_option': r.get('flag_n63_full_option'),
                'flag_n63_pulley_yes': r.get('flag_n63_pulley_yes'),
                'flag_n63_pulley_no': r.get('flag_n63_pulley_no'),
                'flag_pfmot_yes': r.get('flag_pfmot_yes'),
                'flag_pfmot_no': r.get('flag_pfmot_no'),
                'flag_sanden': r.get('flag_sanden'),
                'flag_gearbox_v3': r.get('flag_gearbox_v3'),
                'flag_man_option': r.get('flag_man_option'),
                'flag_not_18t': r.get('flag_not_18t'),
                'flag_urban_kit': r.get('flag_urban_kit'),
                'ac_filter': r.get('ac_filter'),
                'noteeng': r.get('noteeng'),
                'embrague_std': r.get('embrague_std'),
                'embrague_esp': r.get('embrague_esp'),
                'tipus_embrague': r.get('tipus_embrague'),
            })

    return ctx

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'chat_display' not in st.session_state:
    st.session_state.chat_display = []

# ── HEADER ────────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    st.image(os.path.join(BASE, "logo.jpg"), width=200)
with c2:
    st.markdown('<div class="ot-name">Joan P.</div><div class="ot-sub">Kit Selector · OT M&DK</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div style="text-align:right;padding-top:8px"><span class="ot-dot"></span> <span style="font-size:12px;color:#555">En línea</span></div>', unsafe_allow_html=True)
st.divider()

# ── WELCOME ───────────────────────────────────────────────────────────────────
if not st.session_state.chat_display:
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

# ── CHAT ─────────────────────────────────────────────────────────────────────
for role, text in st.session_state.chat_display:
    if role == 'user':
        st.markdown(f'<div class="msg-u"><div class="bubble-u">{text}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="msg-a"><div class="bubble-a">{text}</div></div>', unsafe_allow_html=True)

st.divider()

# ── INPUT ─────────────────────────────────────────────────────────────────────
with st.form(key='chat_form', clear_on_submit=True):
    ci, cb, cn = st.columns([6, 1, 1])
    with ci:
        user_input = st.text_input("", placeholder="Escribe aquí...", label_visibility="collapsed")
    with cb:
        send = st.form_submit_button("➤")
    with cn:
        new_s = st.form_submit_button("↺")

if new_s:
    st.session_state.messages = []
    st.session_state.chat_display = []
    st.rerun()

if send and user_input and user_input.strip():
    msg = user_input.strip()
    st.session_state.chat_display.append(('user', msg))
    st.session_state.messages.append({'role': 'user', 'content': msg})

    with st.spinner("Joan P. está buscando..."):
        # 1. Python extracts state from ALL conversation
        state = extract_state(st.session_state.messages)

        # 2. Python filters DB
        ctx = get_db_context(state, st.session_state.messages)

        # 3. Build API messages with DB context injected into last user message
        api_messages = []
        for m in st.session_state.messages[:-1]:
            api_messages.append({'role': m['role'], 'content': m['content']})
        api_messages.append({
            'role': 'user',
            'content': msg + f'\n\n[DATOS BD]\n{json.dumps(ctx, ensure_ascii=False)}'
        })

        # 4. Claude only writes the response
        client = get_client()
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=api_messages
        )
        reply = resp.content[0].text

    st.session_state.chat_display.append(('bot', reply))
    st.session_state.messages.append({'role': 'assistant', 'content': reply})
    st.rerun()
