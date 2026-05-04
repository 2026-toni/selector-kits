import anthropic
import pandas as pd
import io
import base64
import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
# Lee los CSVs pre-generados — NO el Excel. Así el token count es fijo y controlado.
SEL_CSV     = BASE_DIR / "bd_sel.csv"
NOTES_CSV   = BASE_DIR / "bd_notes.csv"
PROMPT_PATH = BASE_DIR / "prompt_selector_kits_v10.md"

# ── Model ─────────────────────────────────────────────────────────────────────
MODEL = "claude-sonnet-4-5-20250929"

# ── Cache ─────────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT_CACHE = None


def get_system_prompt() -> str:
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        prompt_base = PROMPT_PATH.read_text(encoding="utf-8")
        csv_sel     = SEL_CSV.read_text(encoding="utf-8")
        csv_notes   = NOTES_CSV.read_text(encoding="utf-8")
        _SYSTEM_PROMPT_CACHE = (
            prompt_base
            + "\n\n---\n\n"
            + "## BASE DE DATOS — Tabla de selección (bbdd_kits_v8)\n\n"
            + "```csv\n" + csv_sel   + "\n```\n\n"
            + "## NOTAS TÉCNICAS — noteeng_clean por código\n\n"
            + "```csv\n" + csv_notes + "\n```\n"
        )
    return _SYSTEM_PROMPT_CACHE


def _get_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def chat(messages: list) -> str:
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=2048,
        system=get_system_prompt(),
        messages=messages,
    )
    return response.content[0].text


def chat_with_image(messages: list, image_data: bytes, media_type: str = "image/jpeg") -> str:
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
    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=2048,
        system=get_system_prompt(),
        messages=msgs,
    )
    return response.content[0].text
