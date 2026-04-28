import streamlit as st
import json
import os
import re
from anthropic import Anthropic

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
.stTextInput>div>div>input{border-radius:12px!important;border:1.5px solid #e2e8f0!important;font-family:'Barlow',sans-serif!important;font-size:14px!important}
.stTextInput>div>div>input:focus{border-color:#1B6FC8!important;box-shadow:0 0 0 3px rgba(27,111,200,.1)!important}
.stButton>button{background:linear-gradient(135deg,#1B6FC8,#0A3F7A)!important;color:white!important;border:none!important;border-radius:10px!important;font-family:'Barlow',sans-serif!important;font-weight:600!important}
table{width:100%;border-collapse:collapse;margin:8px 0;font-size:13px}
th{background:#f1f5f9;padding:7px 10px;text-align:left;border:1px solid #e2e8f0;font-weight:600;color:#475569;font-size:11px;text-transform:uppercase}
td{padding:6px 10px;border:1px solid #e2e8f0;color:#1a1a2e}
tr:nth-child(even) td{background:#f8fafc}
</style>
""", unsafe_allow_html=True)

BASE = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_db():
    with open(os.path.join(BASE,"db.json"),"r",encoding="utf-8") as f:
        return json.load(f)

DB = load_db()

SYSTEM_PROMPT = """Eres Joan P., asistente comercial experto en selección de kits para vehículos de OLIVA TORRAS Mount & Drive Kits.

ESTILO: texto natural y conversacional. NUNCA uses ## o ### ni "PASO X". Conciso: máximo 3-4 líneas salvo cuando muestres opciones. Confirma con "✓ [dato]". Una pregunta por turno.

SELECCIÓN FINAL:
✅ **Referencia seleccionada: [CODE]**
Motivo: [modelo] · [motor/cilindrada] · [desde year_from_v4] · [componente] · [diferencial]

📋 **Notas importantes:** (muestra TODO el contenido de noteeng — no omitas nada relevante)

🔧 **Embrague:**
- embrague_esp vacío (tipus=N): "⚠️ Previsto para embrague estándar `[embrague_std]` — no incluido en el kit."
- embrague_esp = embrague_std: "✓ Incluye embrague estándar `[embrague_std]`." + si tipus tiene E/S → ofrecer [CODE]E o [CODE]S
- embrague_esp ≠ embrague_std: "✓ Embrague estándar incluido: `[embrague_std]`." + ofrecer [CODE]E/[CODE]S según tipus

REGLAS: Solo recomiendas códigos existentes en los datos. No inventas datos. Una pregunta por turno.
Excluye STANDARD BRACKET y COMPRESSOR BRACKET. Usa engine_all para mostrar TODOS los motores con cilindrada.
NUNCA digas que un componente no existe si aparece en la lista.
Si los datos muestran resultados, úsalos. Si hay 0 resultados informa al usuario y pregunta de nuevo.

FLUJO (detente al llegar a 1 código):
1. TIPO KIT: KB=A/C · KC=frío industrial · KA=alternador · KH=bomba · KG=generador · KF=chasis
2. MARCA · 3. MODELO (4-8 opciones reales) · 4. TRACCIÓN RWD/FWD si varía
5. ¿VEHÍCULO NUEVO? SÍ=year_to_int NULO · NO=pide año
6. AÑO (si no nuevo) · 7. MOTOR (engine_all con cilindrada) · 8. COMPONENTE
9. FLAGS (solo si varían): gearbox_v3 · auto_tensioner · pfmot_yes/no · urban_kit · ind_belt · n63 · sanden · man_option
10. A/C: ac_filter=any → NO preguntar"""

def filter_db(state):
    data = [r for r in DB
            if r.get('kit_type') != 'Otro'
            and r.get('brand') != 'ACCESSORY'
            and r.get('model_clean') not in ('STANDARD BRACKET','COMPRESSOR BRACKET','STANDARD BOSCH')]

    if state.get('kit_type'):
        data = [r for r in data if r.get('kit_type') == state['kit_type']]
    if state.get('brand'):
        data = [r for r in data if r.get('brand') == state['brand']]
    if state.get('model_clean'):
        data = [r for r in data if r.get('model_clean') == state['model_clean']]
    if state.get('flag_rwd'):
        data = [r for r in data if r.get('flag_rwd') == 1]
    if state.get('flag_fwd'):
        data = [r for r in data if r.get('flag_fwd') == 1]
    if state.get('new_vehicle'):
        data = [r for r in data if r.get('year_to_int') is None]
    elif state.get('year'):
        yr = state['year']
        data = [r for r in data if
                r.get('year_from_int') is not None and
                r['year_from_int'] <= yr and
                (r.get('year_to_int') is None or r['year_to_int'] >= yr)]
    if state.get('component'):
        data = [r for r in data if r.get('nom_opcio_compressor') == state['component']]
    return data

def build_context(data, state):
    if not data:
        return f"[BD: Sin resultados para filtros: {json.dumps(state, ensure_ascii=False)}. Informa al usuario y pide más datos.]"

    by_code = {}
    for r in data:
        if r.get('code') and r['code'] not in by_code:
            by_code[r['code']] = r
    codes = list(by_code.values())
    uniq = lambda lst: list(dict.fromkeys(x for x in lst if x))

    summary = {
        'total_codes': len(codes),
        'filters_active': state,
        'models': uniq(r.get('model_clean') for r in codes),
        'engines': uniq(r.get('engine_all') or r.get('engine_clean') for r in codes),
        'components': uniq(r.get('nom_opcio_compressor') for r in data),
        'tractions': {
            'rwd': sum(1 for r in codes if r.get('flag_rwd') == 1),
            'fwd': sum(1 for r in codes if r.get('flag_fwd') == 1),
        }
    }

    if len(codes) <= 12:
        detail = []
        for r in codes:
            detail.append({
                'code': r.get('code'),
                'model': r.get('model_clean'),
                'engine': r.get('engine_all') or r.get('engine_clean'),
                'cilinder': r.get('cilinder'),
                'year_from_v4': r.get('year_from_v4'),
                'year_to_v4': r.get('year_to_v4'),
                'components': uniq(d.get('nom_opcio_compressor') for d in data if d.get('code') == r.get('code')),
                'flag_rwd': r.get('flag_rwd'), 'flag_fwd': r.get('flag_fwd'), 'flag_awd': r.get('flag_awd'),
                'flag_auto_tensioner': r.get('flag_auto_tensioner'),
                'flag_n63_pulley_yes': r.get('flag_n63_pulley_yes'),
                'flag_n63_pulley_no': r.get('flag_n63_pulley_no'),
                'flag_n63_full_option': r.get('flag_n63_full_option'),
                'flag_pfmot_yes': r.get('flag_pfmot_yes'), 'flag_pfmot_no': r.get('flag_pfmot_no'),
                'flag_urban_kit': r.get('flag_urban_kit'), 'flag_ind_belt': r.get('flag_ind_belt'),
                'flag_sanden': r.get('flag_sanden'), 'flag_gearbox_v3': r.get('flag_gearbox_v3'),
                'flag_man_option': r.get('flag_man_option'), 'flag_not_18t': r.get('flag_not_18t'),
                'ac_filter': r.get('ac_filter'), 'noteeng': r.get('noteeng'),
                'embrague_std': r.get('embrague_std'), 'embrague_esp': r.get('embrague_esp'),
                'tipus_embrague': r.get('tipus_embrague'),
            })
        return f"[BD {len(codes)} códigos]\n[Resumen:{json.dumps(summary,ensure_ascii=False)}]\n[Detalle:{json.dumps(detail,ensure_ascii=False)}]"

    return f"[BD {len(codes)} códigos]\n[Resumen:{json.dumps(summary,ensure_ascii=False)}]"

def extract_state(messages):
    text = ' '.join(m['content'] for m in messages if isinstance(m.get('content'), str))
    s = {}

    # Kit type
    if re.search(r'compresor\s*a/c|\bkb\b', text, re.I): s['kit_type'] = 'Kit compresor A/C'
    elif re.search(r'fr[ií]o\s*industrial|\bkc\b', text, re.I): s['kit_type'] = 'Kit compresor frío industrial'
    elif re.search(r'alternador|\bka\b', text, re.I): s['kit_type'] = 'Kit alternador'
    elif re.search(r'bomba|\bkh\b', text, re.I): s['kit_type'] = 'Kit bomba hidráulica'
    elif re.search(r'generador|\bkg\b', text, re.I): s['kit_type'] = 'Kit generador'
    elif re.search(r'chasis|\bkf\b', text, re.I): s['kit_type'] = 'Kit chasis'

    # Brand
    bmap = [
        (r'sprinter|vito|actros|atego|arocs|antos|axor|econic', 'MERCEDES'),
        (r'ducato|scudo|talento|doblo', 'FIAT'),
        (r'transit|tourneo', 'FORD'),
        (r'\bmaster\b|trafic|kangoo', 'RENAULT'),
        (r'\bdaily\b|eurocargo|stralis|trakker', 'IVECO'),
        (r'\bboxer\b', 'PEUGEOT'),
        (r'jumper|jumpy|berlingo', 'CITROEN'),
        (r'crafter|transporter', 'VW'),
        (r'movano|vivaro|\bcombo\b', 'OPEL'),
        (r'nv400|nv300|interstar|primastar', 'NISSAN'),
        (r'\btgl\b|\btgm\b|\btgs\b|\btgx\b|\bman\b', 'MAN'),
        (r'canter|fuso', 'MITSUBISHI'),
        (r'\bvolvo\b', 'VOLVO'), (r'\bdaf\b', 'DAF'),
        (r'\biveco\b', 'IVECO'), (r'\bford\b', 'FORD'),
        (r'\bfiat\b', 'FIAT'), (r'\bmercedes\b', 'MERCEDES'),
    ]
    for pat, brand in bmap:
        if re.search(pat, text, re.I):
            s['brand'] = brand
            break

    # Model - match against DB models (longer/more specific first)
    all_models = list(dict.fromkeys(r.get('model_clean') for r in DB if r.get('model_clean')))
    for model in sorted(all_models, key=lambda x: -len(str(x))):
        m = str(model)
        if any(x in m.upper() for x in ['BRACKET', 'SEPARADOR', 'BOSCH']):
            continue
        pat = re.escape(m).replace(r'\.', r'\.?').replace(r'\ ', r'\s*')
        if re.search(pat, text, re.I):
            s['model_clean'] = model
            break

    # Traction
    if re.search(r'\brwd\b|tracci[oó]n\s*trasera', text, re.I): s['flag_rwd'] = True
    if re.search(r'\bfwd\b|tracci[oó]n\s*delantera', text, re.I): s['flag_fwd'] = True

    # New vehicle
    if re.search(r'nuevo|reciente|es\s*nuevo|si.*nuevo', text, re.I): s['new_vehicle'] = True

    # Year
    if not s.get('new_vehicle'):
        ym = re.search(r'\b(19[89]\d|20[012]\d)\b', text)
        if ym: s['year'] = int(ym.group(1))

    # Component
    cmap = [
        (r'TM\s*43', 'TM 43'), (r'TM\s*31', 'TM 31 / QP 31'),
        (r'TM\s*21', 'TM 21 / QP 21'), (r'TM\s*16', 'TM 16 / QP 16'),
        (r'TM\s*15', 'TM 15 / QP 15'), (r'TM\s*13', 'TM 13 / QP 13'),
        (r'TM\s*0?8\b', 'TM 08 / QP 08'), (r'QP\s*25', 'QP 25'),
        (r'UP\s*170|UPF\s*170', 'UP 170 / UPF 170'),
        (r'UP\s*150|UPF\s*150', 'UP 150 / UPF 150'),
        (r'UP\s*120|UPF\s*120', 'UP 120 / UPF 120'),
        (r'UPF\s*200', 'UPF 200'), (r'UP\s*90\b', 'UP 90'),
        (r'SD7H15', 'SD7H15'), (r'SD7L15', 'SD7L15'),
        (r'SD5H14', 'SD5H14'), (r'SD5L14', 'SD5L14'),
        (r'CS\s*150', 'CS150'), (r'CS\s*90\b', 'CS90'), (r'CS\s*55\b', 'CS55'),
        (r'CR\s*2323', 'CR2323'), (r'CR\s*2318', 'CR2318'),
        (r'Mahle.*200A|MG\s*29', 'Mahle MG 29 (200A 14V)'),
        (r'Mahle.*100A|MG\s*142', 'Mahle MG 142 (100A 28V)'),
        (r'Valeo|140A\s*14V', 'Valeo 140A 14V'),
        (r'SEG|150A\s*28V', 'SEG 150A 28V '),
        (r'TK.?315', 'TK-315'), (r'TK.?312', 'TK-312'),
        (r'BITZER', 'BITZER 4UFC'), (r'BOCK', 'BOCK FK40'),
        (r'16\s*cc|SALAMI.*16', '16 cc SALAMI'),
        (r'12\s*cc|SALAMI.*12', '12 cc SALAMI'),
        (r'8\s*cc|SALAMI.*8\b', '8 cc SALAMI'),
    ]
    for pat, name in cmap:
        if re.search(pat, text, re.I):
            s['component'] = name
            break

    return s

@st.cache_resource
def get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY', '')
    return Anthropic(api_key=api_key)

# Session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Header
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    st.image(os.path.join(BASE, "logo.jpg"), width=200)
with c2:
    st.markdown('<div class="ot-name">Joan P.</div><div class="ot-sub">Kit Selector · OT M&DK</div>', unsafe_allow_html=True)
with c3:
    st.markdown('<div style="text-align:right;padding-top:8px"><span class="ot-dot"></span> <span style="font-size:12px;color:#555">En línea</span></div>', unsafe_allow_html=True)

st.divider()

# Chat display
if not st.session_state.messages:
    st.markdown("""<div class="wbox">
    <div class="ot-name">👋 Hola, soy Joan P.</div>
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

for msg in st.session_state.messages:
    if msg['role'] == 'user':
        st.markdown(f'<div class="msg-u"><div class="bubble-u">{msg["content"]}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="msg-a"><div class="bubble-a">{msg["content"]}</div></div>', unsafe_allow_html=True)

st.divider()

# Input form — key trick: use st.form to avoid double-submit
with st.form(key='chat_form', clear_on_submit=True):
    ci, cb, cn = st.columns([6, 1, 1])
    with ci:
        user_input = st.text_input("", placeholder="Escribe aquí...", label_visibility="collapsed")
    with cb:
        send = st.form_submit_button("➤")
    with cn:
        new_session = st.form_submit_button("↺")

if new_session:
    st.session_state.messages = []
    st.rerun()

if send and user_input and user_input.strip():
    msg = user_input.strip()
    st.session_state.messages.append({'role': 'user', 'content': msg})

    with st.spinner("Joan P. está buscando..."):
        state = extract_state(st.session_state.messages)
        filtered = filter_db(state)
        ctx = build_context(filtered, state)

        api_msgs = []
        for m in st.session_state.messages[:-1]:
            api_msgs.append({'role': m['role'], 'content': m['content']})
        api_msgs.append({'role': 'user', 'content': msg + '\n\n' + ctx})

        client = get_client()
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=api_msgs
        )
        reply = resp.content[0].text

    st.session_state.messages.append({'role': 'assistant', 'content': reply})
    st.rerun()
