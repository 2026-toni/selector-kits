import anthropic
import pandas as pd
import io
import base64
import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
EXCEL_PATH  = BASE_DIR / "bbdd_kits_v8.xlsx"
PROMPT_PATH = BASE_DIR / "prompt_selector_kits_v10.md"

# ── Model — string exacto verificado en la API de Anthropic ───────────────────
MODEL = "claude-sonnet-4-5-20250929"

# ── Columnas mínimas necesarias para el flujo del prompt v10 ──────────────────
_SEL_COLS = [
    "code", "kit_type", "brand", "model_clean", "engine_all",
    "year_from_int", "year_to_int", "year_confidence", "model_max_year",
    "flag_rwd", "flag_fwd", "flag_awd", "flag_rhd",
    "flag_start_stop", "flag_high_idle", "flag_gearbox_v3", "flag_sanden",
    "flag_auto_tensioner", "flag_pfmot_yes", "flag_pfmot_no",
    "flag_urban_kit", "flag_ind_belt", "flag_n63_full_option",
    "flag_n63_pulley_yes", "flag_n63_pulley_no",
    "flag_himatic", "flag_allison_not", "flag_zf_not",
    "flag_man_option", "flag_engine_sideways",
    "cilinder", "ac_filter",
    "embrague_std", "embrague_esp", "tipus_embrague",
    "year_from_v4", "year_to_v4",
]

# ── Cache del system prompt (se construye solo la primera vez) ────────────────
_SYSTEM_PROMPT_CACHE = None


def _build_system_prompt() -> str:
    df = pd.read_excel(EXCEL_PATH, sheet_name=0, dtype=str).fillna("")

    # Tabla 1: selección (sin noteeng_clean — ahorra ~55% de tokens)
    sel_keep = [c for c in _SEL_COLS if c in df.columns]
    df_sel = df[sel_keep].drop_duplicates()
    buf1 = io.StringIO()
    df_sel.to_csv(buf1, index=False)

    # Tabla 2: notas técnicas (una fila por código único)
    note_cols = [c for c in ["code", "noteeng_clean"] if c in df.columns]
    df_notes = df[note_cols].drop_duplicates(subset=["code"])
    buf2 = io.StringIO()
    df_notes.to_csv(buf2, index=False)

    prompt_base = PROMPT_PATH.read_text(encoding="utf-8")

    return (
        prompt_base
        + "\n\n---\n\n"
        + "## BASE DE DATOS — Tabla de selección (bbdd_kits_v8)\n\n"
        + "```csv\n" + buf1.getvalue() + "\n```\n\n"
        + "## NOTAS TÉCNICAS — noteeng_clean por código\n\n"
        + "```csv\n" + buf2.getvalue() + "\n```\n"
    )


def get_system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        _SYSTEM_PROMPT_CACHE = _build_system_prompt()
    return _SYSTEM_PROMPT_CACHE


# ── Cliente Anthropic ─────────────────────────────────────────────────────────
def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


# ── API pública ───────────────────────────────────────────────────────────────
def chat(messages: list) -> str:
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=get_system_prompt(),
        messages=messages,
    )
    return response.content[0].text


def chat_with_image(messages: list, image_data: bytes, media_type: str = "image/jpeg") -> str:
    client = _get_client()
    img_b64 = base64.standard_b64encode(image_data).decode("utf-8")
    msgs = list(messages)
    last_text = msgs[-1]["content"] if msgs else ""
    msgs[-1] = {
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
            {"type": "text", "text": last_text},
        ],
    }
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=get_system_prompt(),
        messages=msgs,
    )
    return response.content[0].text
