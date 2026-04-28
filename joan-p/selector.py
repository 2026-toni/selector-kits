"""
Motor de selección de kits — lógica Python pura.
Replica exactamente la lógica de filtrado del chat de Claude.
"""
import json, re, os, math

BASE = os.path.dirname(os.path.abspath(__file__))

def load_db():
    with open(os.path.join(BASE, "db.json"), "r", encoding="utf-8") as f:
        return json.load(f)

DB = load_db()

# ── NORMALIZACIÓN DE COMPONENTES ─────────────────────────────────────────────
COMP_MAP = [
    (r'TM\s*43', 'TM 43'), (r'TM\s*31', 'TM 31 / QP 31'),
    (r'TM\s*21', 'TM 21 / QP 21'), (r'TM\s*16', 'TM 16 / QP 16'),
    (r'TM\s*15', 'TM 15 / QP 15'), (r'TM\s*13', 'TM 13 / QP 13'),
    (r'TM\s*0?8\b', 'TM 08 / QP 08'), (r'QP\s*25', 'QP 25'),
    (r'UP\s*170|UPF\s*170', 'UP 170 / UPF 170'),
    (r'UP\s*150|UPF\s*150', 'UP 150 / UPF 150'),
    (r'UP\s*120|UPF\s*120', 'UP 120 / UPF 120'),
    (r'UPF\s*200', 'UPF 200'), (r'UP\s*90\b', 'UP 90'),
    (r'SD7H15', 'SD7H15'), (r'SD7L15', 'SD7L15'),
    (r'SD5H14', 'SD5H14'), (r'SD5L14', 'SD5L14'), (r'SD5H09', 'SD5H09'),
    (r'CS\s*150', 'CS150'), (r'CS\s*90\b', 'CS90'), (r'CS\s*55\b', 'CS55'),
    (r'CR\s*2323', 'CR2323'), (r'CR\s*2318', 'CR2318'),
    (r'Mahle.*200A|MG\s*29|200A.*14V', 'Mahle MG 29 (200A 14V)'),
    (r'Mahle.*100A|MG\s*142|100A.*28V', 'Mahle MG 142 (100A 28V)'),
    (r'Valeo|140A\s*14V', 'Valeo 140A 14V'),
    (r'\bSEG\b|150A\s*28V', 'SEG 150A 28V '),
    (r'G4.*400V?|400V.*G4', 'Generator "G4-400V" '),
    (r'G4.*230V?|230V.*G4', 'Generator "G4-230V"'),
    (r'G3.*400V?|400V.*G3', 'Generator "G3-400V" '),
    (r'G3.*230V?|230V.*G3', 'Generator "G3-230V"'),
    (r'TK.?315', 'TK-315'), (r'TK.?312', 'TK-312'),
    (r'BITZER', 'BITZER 4UFC'), (r'BOCK', 'BOCK FK40'),
    (r'Xarios', 'Xarios Integrated'),
    (r'16\s*cc|SALAMI.*16', '16 cc SALAMI'),
    (r'12\s*cc|SALAMI.*12', '12 cc SALAMI'),
    (r'8\s*cc\b|SALAMI.*8\b', '8 cc SALAMI'),
    (r'HPI\s*15', 'HPI 15cc'), (r'HPI\s*12', 'HPI 12cc'),
    (r'HPI\s*8\b', 'HPI 8cc'), (r'IPH\s*25', 'IPH 25cc'),
    (r'X.?430', 'X-430'), (r'\bELH7\b', 'ELH7'),
    (r'HGX34P', 'HGX34P'), (r'HG34P', 'HG34P'),
]

BRAND_MAP = [
    (r'sprinter|vito|actros|atego|arocs|antos|axor|econic', 'MERCEDES'),
    (r'ducato|scudo|talento|doblo', 'FIAT'),
    (r'transit|tourneo', 'FORD'),
    (r'\bmaster\b|trafic|kangoo', 'RENAULT'),
    (r'\bdaily\b|eurocargo|stralis|trakker', 'IVECO'),
    (r'\bboxer\b|expert\b|partner\b', 'PEUGEOT'),
    (r'jumper|jumpy|berlingo', 'CITROEN'),
    (r'crafter|transporter', 'VW'),
    (r'movano|vivaro|\bcombo\b', 'OPEL'),
    (r'nv400|nv300|interstar|primastar', 'NISSAN'),
    (r'\btgl\b|\btgm\b|\btgs\b|\btgx\b|\bman\b', 'MAN'),
    (r'canter|fuso', 'MITSUBISHI'),
    (r'\bvolvo\b', 'VOLVO'), (r'\bdaf\b', 'DAF'),
    (r'\biveco\b', 'IVECO'), (r'\bford\b', 'FORD'),
    (r'\bfiat\b', 'FIAT'), (r'\bmercedes\b', 'MERCEDES'),
    (r'\brenault\b', 'RENAULT'), (r'\bopel\b', 'OPEL'),
    (r'\bcitroen\b|\bcitroen\b', 'CITROEN'),
    (r'\bpeugeot\b', 'PEUGEOT'), (r'\bnissan\b', 'NISSAN'),
]

KIT_MAP = [
    (r'compresor\s*a/c|\bkb\b', 'Kit compresor A/C'),
    (r'fr[ií]o\s*industrial|\bkc\b', 'Kit compresor frío industrial'),
    (r'alternador|\bka\b', 'Kit alternador'),
    (r'bomba\s*hidr|\bkh\b', 'Kit bomba hidráulica'),
    (r'generador|\bkg\b', 'Kit generador'),
    (r'chasis|\bkf\b', 'Kit chasis'),
]

ALL_MODELS = sorted(
    [r.get('model_clean') for r in DB if r.get('model_clean') and
     r.get('model_clean') not in ('STANDARD BRACKET','COMPRESSOR BRACKET','STANDARD BOSCH')],
    key=lambda x: -len(str(x))
)
ALL_MODELS_UNIQ = list(dict.fromkeys(ALL_MODELS))

def normalize_comp(text):
    for pat, name in COMP_MAP:
        if re.search(pat, text, re.I):
            return name
    return None

def detect_kit_type(text):
    for pat, kt in KIT_MAP:
        if re.search(pat, text, re.I):
            return kt
    return None

def detect_brand(text):
    for pat, brand in BRAND_MAP:
        if re.search(pat, text, re.I):
            return brand
    return None

def detect_model(text):
    for model in ALL_MODELS_UNIQ:
        m = str(model)
        pat = re.escape(m).replace(r'\.', r'\.?').replace(r'\ ', r'\s*')
        if re.search(pat, text, re.I):
            return model
    return None

def detect_year(text):
    m = re.search(r'\b(19[89]\d|20[012]\d)\b', text)
    return int(m.group(1)) if m else None

# ── FILTRADO PYTHON PURO ─────────────────────────────────────────────────────
def base_filter():
    return [r for r in DB
            if r.get('kit_type') != 'Otro'
            and r.get('brand') != 'ACCESSORY'
            and r.get('model_clean') not in ('STANDARD BRACKET','COMPRESSOR BRACKET','STANDARD BOSCH')]

def apply_filters(state):
    data = base_filter()
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
    if state.get('engine_clean'):
        data = [r for r in data if
                r.get('engine_clean') == state['engine_clean'] or
                (r.get('engine_all') and state['engine_clean'] in r.get('engine_all',''))]
    if state.get('component'):
        data = [r for r in data if r.get('nom_opcio_compressor') == state['component']]
    # Flag filters
    for flag in ['flag_auto_tensioner','flag_n63_pulley_yes','flag_n63_full_option',
                 'flag_pfmot_yes','flag_pfmot_no','flag_urban_kit','flag_ind_belt',
                 'flag_sanden','flag_man_option','flag_not_18t','flag_himatic']:
        if state.get(flag) == 1:
            data = [r for r in data if r.get(flag) == 1]
        elif state.get(flag) == 0:
            data = [r for r in data if r.get(flag) != 1]
    if state.get('flag_auto_tensioner_no'):
        data = [r for r in data if r.get('flag_auto_tensioner') != 1]
    if state.get('flag_gearbox_ok'):
        data = [r for r in data if r.get('flag_gearbox_v3') in ('ok', None, '')]
    if state.get('flag_gearbox_not'):
        data = [r for r in data if r.get('flag_gearbox_v3') == 'not']
    if state.get('ac_filter'):
        ac = state['ac_filter']
        if ac == 'yes':
            data = [r for r in data if r.get('ac_filter') in ('yes', 'any')]
        elif ac == 'no':
            data = [r for r in data if r.get('ac_filter') in ('no', 'any')]
    # N63 logic
    if state.get('n63_full'):
        data = [r for r in data if r.get('flag_n63_full_option') == 1]
    elif state.get('n63_only'):
        data = [r for r in data if r.get('flag_n63_pulley_yes') == 1 and r.get('flag_n63_full_option') != 1 and r.get('flag_n63_pulley_no') != 1]
    elif state.get('n63_none'):
        data = [r for r in data if r.get('flag_n63_pulley_no') == 1 or (r.get('flag_n63_pulley_yes') != 1 and r.get('flag_n63_full_option') != 1)]
    return data

def get_unique_codes(data):
    seen = {}
    for r in data:
        code = r.get('code')
        if code and code not in seen:
            seen[code] = r
    return seen

def get_unique_values(data, field):
    return list(dict.fromkeys(r.get(field) for r in data if r.get(field)))

# ── LÓGICA DE PREGUNTAS (FLUJO EXACTO) ───────────────────────────────────────
def next_step(state, data):
    """
    Returns (question_type, question_text, options, is_done)
    Mirrors exactly the selection logic from the main chat.
    """
    codes = get_unique_codes(data)
    n = len(codes)

    # DONE
    if n == 1:
        return ('done', None, list(codes.values())[0], True)
    if n == 0:
        return ('no_result', None, None, True)

    # PASO 1: Kit type
    if not state.get('kit_type'):
        return ('kit_type', '¿Qué tipo de kit necesitas?', [
            ('KB', 'Kit compresor A/C', 'Compresor de aire acondicionado de cabina'),
            ('KC', 'Kit compresor frío industrial', 'Compresor de frío de transporte'),
            ('KA', 'Kit alternador', 'Alternador auxiliar'),
            ('KH', 'Kit bomba hidráulica', 'Bomba hidráulica auxiliar'),
            ('KG', 'Kit generador', 'Generador eléctrico'),
            ('KF', 'Kit chasis', 'Adaptación de chasis'),
        ], False)

    # PASO 2: Brand
    if not state.get('brand'):
        brands = get_unique_values(list(codes.values()), 'brand')
        return ('brand', '¿De qué marca es el vehículo?\n\n💡 España/UE: Permiso de circulación, campo **D.1 Marca**', brands, False)

    # PASO 3: Model
    if not state.get('model_clean'):
        models = get_unique_values(list(codes.values()), 'model_clean')
        return ('model', '¿Cuál es el modelo exacto?\n\n💡 España/UE: Permiso, campos **D.2 Tipo** y **D.3 Denominación comercial**', models, False)

    # PASO 4: Traction (if variants exist)
    has_rwd = any(r.get('flag_rwd') == 1 for r in codes.values())
    has_fwd = any(r.get('flag_fwd') == 1 for r in codes.values())
    if has_rwd and has_fwd and not state.get('flag_rwd') and not state.get('flag_fwd'):
        return ('traction', '¿El vehículo es de tracción trasera (RWD) o delantera (FWD)?\n\n💡 Árbol de transmisión trasero = RWD. O campo **Variante** del permiso.', ['RWD', 'FWD'], False)

    # PASO 5: New vehicle?
    if state.get('new_vehicle') is None and state.get('year') is None:
        return ('new_vehicle', '¿Es un vehículo de matriculación reciente (nuevo)?', ['Sí, es nuevo', 'No, tengo el año exacto'], False)

    # PASO 6: Year (if not new)
    if state.get('new_vehicle') is False and not state.get('year'):
        return ('year', '¿Sabes el año de fabricación o **primera matriculación**?\n\n💡 España/UE: Permiso, campo **B. Fecha de primera matriculación**', None, False)

    # PASO 7: Engine (if multiple)
    engines = get_unique_values(list(codes.values()), 'engine_all')
    if len(engines) > 1 and not state.get('engine_clean'):
        # Format with cilinder info
        engine_opts = []
        for code_data in codes.values():
            eng = code_data.get('engine_all') or code_data.get('engine_clean', '')
            cil = code_data.get('cilinder', '')
            if eng and eng not in [e[0] for e in engine_opts]:
                engine_opts.append((eng, cil))
        return ('engine', '¿Qué motor tiene el vehículo?\n\n💡 España/UE: Permiso campo **P.5** o etiqueta en tapa de válvulas', engine_opts, False)

    # PASO 8: Component
    components = get_unique_values(data, 'nom_opcio_compressor')
    if len(components) > 1 and not state.get('component'):
        # Group by type
        groups = {}
        for c in components:
            if re.search(r'^TM|^QP', c): g = '🔵 TM / QUE / UNICLA'
            elif re.search(r'^UP|^UPF', c): g = '🟢 UP / UPF'
            elif re.search(r'^SD', c): g = '🔴 SANDEN'
            elif re.search(r'^CS|^CR|^TK|^X-|^Xarios', c): g = '🟡 Carrier / Thermo King'
            elif re.search(r'Mahle|Valeo|SEG|Bosch', c): g = '⚡ Alternador'
            elif re.search(r'Generator', c): g = '🔌 Generador'
            elif re.search(r'SALAMI|HPI|IPH|cc', c): g = '💧 Bomba hidráulica'
            else: g = '⚙️ Otros'
            groups.setdefault(g, []).append(c)
        return ('component', '¿Qué compresor/componente necesitas instalar?', groups, False)

    # PASO 9: Flags — tensor automático
    has_auto_t = any(r.get('flag_auto_tensioner') == 1 for r in codes.values())
    has_manual_t = any(r.get('flag_auto_tensioner') != 1 for r in codes.values())
    if has_auto_t and has_manual_t and 'flag_auto_tensioner_no' not in state and state.get('flag_auto_tensioner') is None:
        return ('tensor', '¿Quieres el kit con tensor automático (intervalos de mantenimiento más largos) o tensor estándar?',
                ['Tensor automático', 'Tensor estándar'], False)

    # PASO 9b: PFMot
    has_pfmot_y = any(r.get('flag_pfmot_yes') == 1 for r in codes.values())
    has_pfmot_n = any(r.get('flag_pfmot_no') == 1 for r in codes.values())
    if has_pfmot_y and has_pfmot_n and 'flag_pfmot_yes' not in state and 'flag_pfmot_no' not in state:
        return ('pfmot', '¿El vehículo tiene la opción PTO / PFMot instalada de fábrica?', ['Sí, tiene PFMot/PTO', 'No tiene PFMot/PTO'], False)

    # PASO 9c: Polea N62/N63
    has_n63_full = any(r.get('flag_n63_full_option') == 1 for r in codes.values())
    has_n63_yes = any(r.get('flag_n63_pulley_yes') == 1 for r in codes.values())
    has_n63_no = any(r.get('flag_n63_pulley_no') == 1 for r in codes.values())
    n63_variants = sum([has_n63_full, has_n63_yes, has_n63_no])
    if n63_variants > 1 and 'n63_full' not in state and 'n63_only' not in state and 'n63_none' not in state:
        opts = []
        if has_n63_full: opts.append('Sí, con bracket original completo (opción N63)')
        if has_n63_yes and not has_n63_full: opts.append('Sí, solo la polea (sin bracket original)')
        if has_n63_no: opts.append('No lleva polea N62/N63')
        return ('n63', '¿El vehículo lleva instalada la polea de cigüeñal N62/N63 (ref. A654 032 10 00)?', opts, False)

    # PASO 9d: SANDEN
    has_sanden = any(r.get('flag_sanden') == 1 for r in codes.values())
    has_no_sanden = any(r.get('flag_sanden') != 1 for r in codes.values())
    if has_sanden and has_no_sanden and 'flag_sanden' not in state:
        return ('sanden', '¿El compresor original del vehículo es de marca SANDEN (modelos SD...)?', ['Sí, es SANDEN', 'No es SANDEN'], False)

    # PASO 9e: AWD
    has_awd = any(r.get('flag_awd') == 1 for r in codes.values())
    has_no_awd = any(r.get('flag_awd') != 1 for r in codes.values())
    if has_awd and has_no_awd and 'is_awd' not in state:
        return ('awd', '¿El vehículo es AWD / 4x4?', ['Sí, es AWD/4x4', 'No, no es AWD'], False)

    # PASO 9f: Gearbox
    gearbox_vals = set(r.get('flag_gearbox_v3') for r in codes.values())
    gearbox_vals = {v for v in gearbox_vals if v}
    has_ok = 'ok' in gearbox_vals
    has_not = 'not' in gearbox_vals
    if (has_ok or has_not) and 'flag_gearbox_ok' not in state and 'flag_gearbox_not' not in state:
        return ('gearbox', '¿El vehículo tiene caja de cambios automática?', ['Sí, caja automática', 'No, caja manual'], False)

    # PASO 10: A/C
    ac_vals = set(r.get('ac_filter') for r in codes.values())
    if 'yes' in ac_vals and 'no' in ac_vals and 'ac_filter' not in state:
        return ('ac', '¿El vehículo tiene aire acondicionado de fábrica?\n\n💡 Inspección visual: compresor A/C visible en el motor', ['Sí, tiene A/C', 'No tiene A/C'], False)

    # Si quedan varios — mostrar tabla comparativa
    return ('compare', None, codes, False)


def process_answer(state, step_type, answer, data):
    """Update state based on user answer and return new state."""
    s = state.copy()
    text = answer.lower()

    if step_type == 'kit_type':
        kt_map = {
            'kb': 'Kit compresor A/C', 'a/c': 'Kit compresor A/C',
            'kc': 'Kit compresor frío industrial', 'frío': 'Kit compresor frío industrial', 'frio': 'Kit compresor frío industrial',
            'ka': 'Kit alternador', 'alternador': 'Kit alternador',
            'kh': 'Kit bomba hidráulica', 'bomba': 'Kit bomba hidráulica',
            'kg': 'Kit generador', 'generador': 'Kit generador',
            'kf': 'Kit chasis', 'chasis': 'Kit chasis',
        }
        for key, val in kt_map.items():
            if key in text:
                s['kit_type'] = val
                break

    elif step_type == 'brand':
        brand = detect_brand(answer)
        if brand:
            s['brand'] = brand
        else:
            # Try exact match from options
            codes = get_unique_codes(data)
            brands = get_unique_values(list(codes.values()), 'brand')
            for b in brands:
                if b.lower() in text or text in b.lower():
                    s['brand'] = b
                    break

    elif step_type == 'model':
        model = detect_model(answer)
        if model:
            s['model_clean'] = model
        else:
            codes = get_unique_codes(data)
            models = get_unique_values(list(codes.values()), 'model_clean')
            for m in sorted(models, key=lambda x: -len(x)):
                pat = re.escape(m).replace(r'\.', r'\.?').replace(r'\ ', r'\s*')
                if re.search(pat, answer, re.I):
                    s['model_clean'] = m
                    break

    elif step_type == 'traction':
        if 'rwd' in text or 'trasera' in text or 'rear' in text:
            s['flag_rwd'] = True
        elif 'fwd' in text or 'delantera' in text or 'front' in text:
            s['flag_fwd'] = True

    elif step_type == 'new_vehicle':
        if re.search(r'\bsí\b|si\b|nuevo|reciente|yes', text, re.I):
            s['new_vehicle'] = True
        else:
            s['new_vehicle'] = False

    elif step_type == 'year':
        yr = detect_year(answer)
        if yr:
            s['year'] = yr

    elif step_type == 'engine':
        # Try to match against available engines
        new_data = apply_filters(s)
        codes = get_unique_codes(new_data)
        for code_data in codes.values():
            eng = code_data.get('engine_all') or code_data.get('engine_clean', '')
            # Check each engine in engine_all
            for part in eng.split('|'):
                part = part.strip()
                if re.search(re.escape(part[:10]), answer, re.I) or \
                   any(kw in answer.upper() for kw in part.upper().split()[:3]):
                    s['engine_clean'] = part
                    break
            if s.get('engine_clean'):
                break
        # Also try direct regex
        if not s.get('engine_clean'):
            for code_data in codes.values():
                eng = code_data.get('engine_all') or code_data.get('engine_clean', '')
                if re.search(re.escape(eng[:15]), answer, re.I):
                    s['engine_clean'] = code_data.get('engine_clean')
                    break

    elif step_type == 'component':
        comp = normalize_comp(answer)
        if comp:
            s['component'] = comp
        else:
            # Try partial match
            new_data = apply_filters(s)
            components = get_unique_values(new_data, 'nom_opcio_compressor')
            for c in components:
                if c.lower() in text or any(w in text for w in c.lower().split()[:2]):
                    s['component'] = c
                    break

    elif step_type == 'tensor':
        if 'automático' in text or 'auto' in text:
            s['flag_auto_tensioner'] = 1
        else:
            s['flag_auto_tensioner_no'] = True

    elif step_type == 'pfmot':
        if re.search(r'\bsí\b|si\b|yes|tiene|con', text, re.I):
            s['flag_pfmot_yes'] = 1
        else:
            s['flag_pfmot_no'] = 1

    elif step_type == 'n63':
        if 'bracket' in text or 'completa' in text or 'completo' in text:
            s['n63_full'] = True
        elif 'solo' in text or 'solo la polea' in text:
            s['n63_only'] = True
        else:
            s['n63_none'] = True

    elif step_type == 'sanden':
        if re.search(r'\bsí\b|si\b|yes|sanden|es sanden', text, re.I):
            s['flag_sanden'] = 1
        else:
            s['flag_sanden'] = 0

    elif step_type == 'awd':
        if re.search(r'\bsí\b|si\b|yes|awd|4x4', text, re.I):
            # Filter by AWD — keep codes with flag_awd=1
            s['is_awd'] = True
        else:
            s['is_awd'] = False

    elif step_type == 'gearbox':
        if re.search(r'automática|automatica|auto|sí\b|si\b|yes', text, re.I):
            s['flag_gearbox_ok'] = True
        else:
            # Manual - exclude 'not' codes
            s['flag_gearbox_ok'] = True  # manual is valid for both ok and empty

    elif step_type == 'ac':
        if re.search(r'\bsí\b|si\b|yes|tiene|con', text, re.I):
            s['ac_filter'] = 'yes'
        else:
            s['ac_filter'] = 'no'

    return s


def apply_awd_filter(data, state):
    """Apply AWD filter if set."""
    if state.get('is_awd') is True:
        return [r for r in data if r.get('flag_awd') == 1]
    elif state.get('is_awd') is False:
        return [r for r in data if r.get('flag_awd') != 1]
    return data


def get_final_result(code_data, all_data):
    """Format the final selection result."""
    code = code_data.get('code', '')
    model = code_data.get('model_clean', '')
    engine = code_data.get('engine_all') or code_data.get('engine_clean', '')
    cil = code_data.get('cilinder', '')
    year_from = code_data.get('year_from_v4', '')
    component = code_data.get('nom_opcio_compressor', '')

    # Get all components for this code
    all_comps = list(dict.fromkeys(
        r.get('nom_opcio_compressor') for r in all_data
        if r.get('code') == code and r.get('nom_opcio_compressor')
    ))

    noteeng = code_data.get('noteeng', '') or ''
    noteeng = noteeng.replace('_x000D_', '').replace('\r', '').strip()

    emb_std = (code_data.get('embrague_std') or '').replace('\\n', ' · ').strip()
    emb_esp = (code_data.get('embrague_esp') or '').replace('\\n', ' · ').strip()
    tipus = code_data.get('tipus_embrague') or ''

    return {
        'code': code,
        'model': model,
        'engine': engine,
        'cilinder': cil,
        'year_from': year_from,
        'component': component,
        'all_components': all_comps,
        'noteeng': noteeng,
        'embrague_std': emb_std,
        'embrague_esp': emb_esp,
        'tipus_embrague': tipus,
    }
