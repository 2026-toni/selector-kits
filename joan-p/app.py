import streamlit as st
import os, json, re
from anthropic import Anthropic
from selector import apply_filters, apply_awd_filter, get_unique_codes, get_unique_values, normalize_comp, detect_brand, detect_model, DB

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

# ── TOOL DEFINITIONS ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "filter_kits",
        "description": """Filtra la base de datos de kits según los criterios proporcionados y devuelve los candidatos.
Usa esta herramienta en CADA paso de la selección para obtener los datos actualizados.
Siempre llama a esta herramienta antes de responder al usuario.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "kit_type": {"type": "string", "description": "Tipo de kit: 'Kit compresor A/C', 'Kit compresor frío industrial', 'Kit alternador', 'Kit bomba hidráulica', 'Kit generador', 'Kit chasis'"},
                "brand": {"type": "string", "description": "Marca del vehículo: MERCEDES, FIAT, FORD, RENAULT, IVECO, PEUGEOT, CITROEN, VW, OPEL, NISSAN, MAN, MITSUBISHI, VOLVO, DAF, etc."},
                "model_clean": {"type": "string", "description": "Modelo exacto del vehículo (debe coincidir exactamente con la BD)"},
                "flag_rwd": {"type": "boolean", "description": "True si tracción trasera RWD"},
                "flag_fwd": {"type": "boolean", "description": "True si tracción delantera FWD"},
                "new_vehicle": {"type": "boolean", "description": "True si vehículo nuevo (filtra year_to_int IS NULL)"},
                "year": {"type": "integer", "description": "Año de fabricación o primera matriculación"},
                "engine_clean": {"type": "string", "description": "Motor exacto del vehículo"},
                "component": {"type": "string", "description": "Componente a instalar (nombre exacto de la BD)"},
                "flag_auto_tensioner": {"type": "boolean", "description": "True = tensor automático, False = tensor estándar"},
                "flag_n63_full": {"type": "boolean", "description": "True = polea N63 con bracket completo"},
                "flag_n63_only": {"type": "boolean", "description": "True = solo polea N63 sin bracket"},
                "flag_n63_none": {"type": "boolean", "description": "True = sin polea N63"},
                "flag_pfmot_yes": {"type": "boolean", "description": "True = tiene PFMot/PTO"},
                "flag_pfmot_no": {"type": "boolean", "description": "True = sin PFMot/PTO"},
                "flag_sanden": {"type": "boolean", "description": "True = compresor SANDEN"},
                "flag_awd": {"type": "boolean", "description": "True = AWD/4x4"},
                "ac_yes": {"type": "boolean", "description": "True = tiene A/C de fábrica"},
                "ac_no": {"type": "boolean", "description": "True = sin A/C"},
            },
            "required": []
        }
    }
]

SYSTEM_PROMPT = """Eres Joan P., asistente comercial experto en selección de kits de OLIVA TORRAS Mount & Drive Kits.

REGLA CRÍTICA: Debes llamar a la herramienta `filter_kits` en CADA respuesta, antes de contestar al usuario.
Los datos que te devuelve la herramienta son la ÚNICA fuente de verdad. No inventes datos ni códigos.

ESTILO: texto natural y conversacional. Sin ## ni "PASO X". Conciso (3-4 líneas máximo salvo tablas). Una pregunta por turno. Confirma con "✓ [dato]".

FLUJO OBLIGATORIO (sigue este orden exacto, detente cuando quede 1 código):

1. TIPO DE KIT — primera pregunta siempre:
   KB=compresor A/C · KC=frío industrial · KA=alternador · KH=bomba · KG=generador · KF=chasis

2. MARCA — campo brand del resultado.
   💡 España/UE: Permiso circulación campo D.1

3. MODELO — muestra 4-8 opciones reales de model_clean del resultado.
   💡 Permiso campos D.2 y D.3

4. TRACCIÓN — si el resultado tiene tanto flag_rwd como flag_fwd en distintos códigos:
   "¿Tracción trasera (RWD) o delantera (FWD)?"
   💡 Árbol de transmisión trasero = RWD

5. ¿VEHÍCULO NUEVO? — "¿Es un vehículo de matriculación reciente?"
   SÍ → usa new_vehicle=true en la herramienta (filtra vigentes sin fecha fin)
   NO → pide año exacto

6. AÑO — "¿Año de fabricación o primera matriculación?"
   💡 Permiso campo B

7. MOTOR — usa engine_all del resultado. Muestra TODOS los motores con cilindrada.
   💡 Permiso campo P.5 o etiqueta tapa válvulas

8. COMPONENTE — agrupa por tipo. Muestra opciones reales.
   TM15=TM 15/QP 15, TM13=TM 13/QP 13, etc.

9. FLAGS KIT (solo si varían entre candidatos del resultado):
   - tensor: flag_auto_tensioner → "¿Tensor automático o estándar?"
   - PFMot: flag_pfmot_yes/no → "¿Tiene PTO/PFMot de fábrica?"
   - N63: flag_n63 → "¿Lleva polea cigüeñal N62/N63?"
   - SANDEN: flag_sanden → "¿Compresor original SANDEN?"
   - AWD: flag_awd → "¿Es AWD/4x4?"
   - Caja: flag_gearbox_v3 (ok/not/vacío) → "¿Caja automática?" (solo si hay mezcla)
   - Opción MAN: flag_man_option → "¿Tiene opción fábrica MAN 120FF/0P0GP?"

10. A/C — solo si ac_filter mezcla yes/no en el resultado:
    "¿Tiene A/C de fábrica?" (ac_filter=any → NO preguntar)

SELECCIÓN FINAL (cuando el resultado tiene 1 código):
✅ **Referencia seleccionada: [CODE]**
Motivo: [modelo] · [motor + cilindrada] · [desde year_from_v4] · [componente] · [diferencial]

📋 **Notas importantes:** (muestra TODO el noteeng — no omitas nada)

🔧 **Embrague:**
- embrague_esp vacío (tipus=N): "⚠️ Previsto para embrague estándar `[embrague_std]` — no incluido en el kit."
- embrague_esp = embrague_std: "✓ Incluye embrague estándar `[embrague_std]`." + si N-E → "También: **[CODE]E**" + si N-S → "**[CODE]S**"
- embrague_esp ≠ embrague_std: "✓ Estándar incluido: `[embrague_std]`. Versión especial: **[CODE]E/S** `[embrague_esp]`"

IMPORTANTE: Excluye STANDARD BRACKET y COMPRESSOR BRACKET. Si no hay resultados, informa y pide más datos."""

def run_tool(tool_input):
    """Execute the filter_kits tool with Python logic."""
    state = {}

    if tool_input.get('kit_type'): state['kit_type'] = tool_input['kit_type']
    if tool_input.get('brand'): state['brand'] = tool_input['brand']
    if tool_input.get('model_clean'): state['model_clean'] = tool_input['model_clean']
    if tool_input.get('flag_rwd'): state['flag_rwd'] = True
    if tool_input.get('flag_fwd'): state['flag_fwd'] = True
    if tool_input.get('new_vehicle'): state['new_vehicle'] = True
    if tool_input.get('year'): state['year'] = int(tool_input['year'])
    if tool_input.get('engine_clean'): state['engine_clean'] = tool_input['engine_clean']
    if tool_input.get('component'): state['component'] = tool_input['component']
    if tool_input.get('flag_auto_tensioner') is True: state['flag_auto_tensioner'] = 1
    if tool_input.get('flag_auto_tensioner') is False: state['flag_auto_tensioner_no'] = True
    if tool_input.get('flag_n63_full'): state['n63_full'] = True
    if tool_input.get('flag_n63_only'): state['n63_only'] = True
    if tool_input.get('flag_n63_none'): state['n63_none'] = True
    if tool_input.get('flag_pfmot_yes'): state['flag_pfmot_yes'] = 1
    if tool_input.get('flag_pfmot_no'): state['flag_pfmot_no'] = 1
    if tool_input.get('flag_sanden') is True: state['flag_sanden'] = 1
    if tool_input.get('flag_sanden') is False: state['flag_sanden'] = 0
    if tool_input.get('flag_awd') is True: state['is_awd'] = True
    if tool_input.get('flag_awd') is False: state['is_awd'] = False
    if tool_input.get('ac_yes'): state['ac_filter'] = 'yes'
    if tool_input.get('ac_no'): state['ac_filter'] = 'no'

    data = apply_filters(state)
    data = apply_awd_filter(data, state)

    by_code = {}
    for r in data:
        if r.get('code') and r['code'] not in by_code:
            by_code[r['code']] = r

    codes = list(by_code.values())
    uniq = lambda lst: list(dict.fromkeys(x for x in lst if x))

    result = {
        'total_codes': len(codes),
        'filters_used': {k: v for k, v in state.items()},
        'available_models': uniq(r.get('model_clean') for r in codes),
        'available_brands': uniq(r.get('brand') for r in codes),
        'available_engines': [
            {'engine': r.get('engine_all') or r.get('engine_clean'), 'cilinder': r.get('cilinder')}
            for r in codes
        ],
        'available_components': uniq(r.get('nom_opcio_compressor') for r in data),
        'traction': {
            'has_rwd': any(r.get('flag_rwd') == 1 for r in codes),
            'has_fwd': any(r.get('flag_fwd') == 1 for r in codes),
        },
        'flags_present': {
            'auto_tensioner_yes': any(r.get('flag_auto_tensioner') == 1 for r in codes),
            'auto_tensioner_no': any(r.get('flag_auto_tensioner') != 1 for r in codes),
            'pfmot_yes': any(r.get('flag_pfmot_yes') == 1 for r in codes),
            'pfmot_no': any(r.get('flag_pfmot_no') == 1 for r in codes),
            'n63_full': any(r.get('flag_n63_full_option') == 1 for r in codes),
            'n63_yes': any(r.get('flag_n63_pulley_yes') == 1 for r in codes),
            'n63_no': any(r.get('flag_n63_pulley_no') == 1 for r in codes),
            'sanden_yes': any(r.get('flag_sanden') == 1 for r in codes),
            'sanden_no': any(r.get('flag_sanden') != 1 for r in codes),
            'awd_yes': any(r.get('flag_awd') == 1 for r in codes),
            'awd_no': any(r.get('flag_awd') != 1 for r in codes),
            'man_option': any(r.get('flag_man_option') == 1 for r in codes),
            'gearbox_ok': any(r.get('flag_gearbox_v3') == 'ok' for r in codes),
            'gearbox_not': any(r.get('flag_gearbox_v3') == 'not' for r in codes),
        },
        'ac_values': uniq(r.get('ac_filter') for r in codes),
    }

    if len(codes) <= 12:
        result['candidates'] = []
        for r in codes:
            result['candidates'].append({
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
                'flag_urban_kit': r.get('flag_urban_kit'),
                'flag_sanden': r.get('flag_sanden'),
                'flag_gearbox_v3': r.get('flag_gearbox_v3'),
                'flag_man_option': r.get('flag_man_option'),
                'flag_not_18t': r.get('flag_not_18t'),
                'ac_filter': r.get('ac_filter'),
                'noteeng': r.get('noteeng'),
                'embrague_std': r.get('embrague_std'),
                'embrague_esp': r.get('embrague_esp'),
                'tipus_embrague': r.get('tipus_embrague'),
            })

    return json.dumps(result, ensure_ascii=False)

@st.cache_resource
def get_client():
    api_key = os.environ.get('ANTHROPIC_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY', '')
    return Anthropic(api_key=api_key)

def call_claude_with_tools(messages):
    """Call Claude with tool_use loop."""
    client = get_client()
    api_messages = list(messages)

    while True:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=api_messages
        )

        # Check if Claude wants to use a tool
        tool_uses = [b for b in resp.content if b.type == 'tool_use']

        if not tool_uses:
            # Claude responded without tool — return text
            text_blocks = [b for b in resp.content if b.type == 'text']
            return text_blocks[0].text if text_blocks else ""

        # Execute all tool calls
        tool_results = []
        for tool_use in tool_uses:
            if tool_use.name == 'filter_kits':
                result = run_tool(tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

        # Add assistant response and tool results to messages
        api_messages.append({"role": "assistant", "content": resp.content})
        api_messages.append({"role": "user", "content": tool_results})

        # If stop_reason is end_turn after tool use, loop again to get final response
        if resp.stop_reason == 'end_turn':
            break

    # Final response after tool use
    resp2 = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=api_messages
    )
    text_blocks = [b for b in resp2.content if b.type == 'text']
    return text_blocks[0].text if text_blocks else ""

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = []  # list of {role, content} for API
if 'chat_display' not in st.session_state:
    st.session_state.chat_display = []  # list of (role, text) for display

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

# ── CHAT DISPLAY ──────────────────────────────────────────────────────────────
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
        reply = call_claude_with_tools(st.session_state.messages)

    st.session_state.chat_display.append(('bot', reply))
    st.session_state.messages.append({'role': 'assistant', 'content': reply})
    st.rerun()
