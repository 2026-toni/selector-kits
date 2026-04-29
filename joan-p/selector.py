"""
selector.py — Filtrado Python puro sobre la BD.
Claude gestiona todo el flujo de selección. Python solo filtra.
"""
import pandas as pd
import os, re, json

BASE = os.path.dirname(os.path.abspath(__file__))

KEY_COLS = [
    'code','kit_type','brand','model_clean','engine_clean','engine_all',
    'cilinder','year_from_v4','year_to_v4','year_from_int','year_to_int',
    'year_confidence','model_max_year','nom_opcio_compressor','noteeng_clean',
    'ac_filter','embrague_std','embrague_esp','tipus_embrague',
    'flag_rwd','flag_fwd','flag_awd','flag_rhd','flag_start_stop','flag_high_idle',
    'flag_gearbox_v3','flag_auto_tensioner','flag_two_auto_tensioners',
    'flag_pfmot_yes','flag_pfmot_no','flag_urban_kit','flag_ind_belt',
    'flag_n63_pulley_yes','flag_n63_pulley_no','flag_n63_full_option',
    'flag_sanden','flag_man_option','flag_not_18t','flag_himatic',
    'flag_allison_not','flag_zf_not'
]

EXCLUDE_COMPONENTS = {'STANDARD BRACKET', 'COMPRESSOR BRACKET', 'STANDARD BOSCH'}
EXCLUDE_BRANDS = {'ACCESSORY'}
EXCLUDE_KIT_TYPES = {'Otro'}


def load_db():
    """Load and cache the BD from Excel. Robust path for Streamlit Cloud."""
    candidates = [
        os.path.join(BASE, "bbdd_kits_v6.xlsx"),
        os.path.join(os.getcwd(), "bbdd_kits_v6.xlsx"),
        os.path.join(os.getcwd(), "joan-p", "bbdd_kits_v6.xlsx"),
        "/mount/src/selector-kits/joan-p/bbdd_kits_v6.xlsx",
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if path is None:
        raise FileNotFoundError(
            f"No se encontró bbdd_kits_v6.xlsx. Rutas probadas: {candidates}"
        )
    df = pd.read_excel(path, sheet_name="Sheet1")
    available = [c for c in KEY_COLS if c in df.columns]
    df = df[available]
    # Exclude invalid rows
    df = df[~df['kit_type'].isin(EXCLUDE_KIT_TYPES)]
    df = df[~df['brand'].isin(EXCLUDE_BRANDS)]
    df = df[~df['nom_opcio_compressor'].isin(EXCLUDE_COMPONENTS)]
    return df

_DB = None

def get_db():
    global _DB
    if _DB is None:
        _DB = load_db()
    return _DB


def get_kit_types():
    """Return all available kit types."""
    df = get_db()
    return sorted(df['kit_type'].dropna().unique().tolist())


def get_brands(kit_type=None):
    """Return brands, optionally filtered by kit_type."""
    df = get_db()
    if kit_type:
        df = df[df['kit_type'] == kit_type]
    return sorted(df['brand'].dropna().unique().tolist())


def get_models(kit_type=None, brand=None):
    """Return models, optionally filtered."""
    df = get_db()
    if kit_type:
        df = df[df['kit_type'] == kit_type]
    if brand:
        df = df[df['brand'] == brand]
    return sorted(df['model_clean'].dropna().unique().tolist())


def filter_candidates(kit_type=None, brand=None, model=None, max_rows=300):
    """
    Pre-filter BD by kit_type + brand + model.
    Returns a list of dicts (slim rows) for Claude to process.
    Capped at max_rows to keep context manageable.
    """
    df = get_db()

    if kit_type:
        df = df[df['kit_type'] == kit_type]
    if brand:
        df = df[df['brand'] == brand]
    if model:
        df = df[df['model_clean'] == model]

    if len(df) > max_rows:
        df = df.head(max_rows)

    # Convert to clean dicts, replace NaN with None
    records = df.where(pd.notna(df), None).to_dict('records')
    return records


def candidates_to_json(records, max_chars=80000):
    """Serialize candidate records to JSON string, truncated if needed."""
    text = json.dumps(records, ensure_ascii=False, default=str)
    if len(text) > max_chars:
        # Reduce to fit
        while len(records) > 10 and len(text) > max_chars:
            records = records[:int(len(records)*0.8)]
            text = json.dumps(records, ensure_ascii=False, default=str)
    return text


def detect_kit_type(text):
    """Detect kit type from free text."""
    patterns = [
        (r'compresor\s*a/?c|\bkb\b|aire\s*acond', 'Kit compresor A/C'),
        (r'fr[íi]o\s*industrial|\bkc\b|frigor', 'Kit compresor frío industrial'),
        (r'alternador|\bka\b', 'Kit alternador'),
        (r'bomba\s*hidr|\bkh\b', 'Kit bomba hidráulica'),
        (r'generador|\bkg\b', 'Kit generador'),
        (r'chasis|\bkf\b', 'Kit chasis'),
    ]
    t = text.lower()
    for pat, kt in patterns:
        if re.search(pat, t, re.I):
            return kt
    return None


def detect_brand(text):
    """Detect brand from free text."""
    brand_patterns = [
        (r'\bsprinter\b|\bvito\b|\bactros\b|\batego\b|\barocs\b|\bantos\b|\baxor\b|\beconic\b', 'MERCEDES'),
        (r'\bducato\b|\bscudo\b|\btalento\b|\bdoblo\b', 'FIAT'),
        (r'\btransit\b|\btourneo\b|\bford\b', 'FORD'),
        (r'\bmaster\b|\btrafic\b|\bkangoo\b|\brenault\b', 'RENAULT'),
        (r'\bdaily\b|\beurocargo\b|\bstralis\b|\biveco\b', 'IVECO'),
        (r'\bboxer\b|\bexpert\b|\bpartner\b|\bpeugeot\b', 'PEUGEOT'),
        (r'\bjumper\b|\bjumpy\b|\bberlingo\b|\bcitroen\b', 'CITROEN'),
        (r'\bcrafter\b|\btransporter\b|\bvw\b|\bvolkswagen\b', 'VW'),
        (r'\bmovano\b|\bvivaro\b|\bcombo\b|\bopel\b', 'OPEL'),
        (r'\bnv400\b|\bnv300\b|\binterstar\b|\bnissan\b', 'NISSAN'),
        (r'\btgl\b|\btgm\b|\btgs\b|\btgx\b|\bman\b', 'MAN'),
        (r'\bcanter\b|\bfuso\b|\bmitsubishi\b', 'MITSUBISHI'),
        (r'\bvolvo\b', 'VOLVO'),
        (r'\bdaf\b', 'DAF'),
        (r'\bscania\b', 'SCANIA'),
        (r'\bisuzu\b', 'ISUZU'),
        (r'\btoyota\b', 'TOYOTA'),
        (r'\bvw\b|\bvolkswagen\b', 'VW'),
        (r'\bmercedes\b', 'MERCEDES'),
    ]
    t = text.lower()
    for pat, brand in brand_patterns:
        if re.search(pat, t, re.I):
            return brand
    return None


def get_model_max_year(kit_type, brand, model):
    """Get the maximum year for a model+kit_type combination."""
    df = get_db()
    mask = (df['kit_type'] == kit_type) & (df['brand'] == brand) & (df['model_clean'] == model)
    sub = df[mask]
    if sub.empty:
        return None
    val = sub['model_max_year'].max()
    return int(val) if pd.notna(val) else None
