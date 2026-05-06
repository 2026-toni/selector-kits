import anthropic
import base64
import json
import os
from pathlib import Path

MODEL = "claude-sonnet-4-5"
BASE  = Path(__file__).parent

_PROMPT_CACHE = None
_BD_CACHE     = {}
_KIT_INDEX    = None


def _get_kit_index() -> dict:
    global _KIT_INDEX
    if _KIT_INDEX is None:
        _KIT_INDEX = json.loads(
            (BASE / "kit_index.json").read_text(encoding="utf-8"))
    return _KIT_INDEX


def _get_prompt_base() -> str:
    global _PROMPT_CACHE
    if _PROMPT_CACHE is None:
        _PROMPT_CACHE = (BASE / "prompt_selector_kits_v10.md").read_text(encoding="utf-8")
    return _PROMPT_CACHE


def _get_bd(brand: str, kit_type: str) -> str:
    key = f"{brand}|{kit_type}"
    if key not in _BD_CACHE:
        idx   = _get_kit_index()
        entry = idx.get(key, {})
        fname = entry.get("file", "")
        if fname:
            csv_path = BASE / "bd_kits" / fname
            _BD_CACHE[key] = csv_path.read_text(encoding="utf-8")
        else:
            _BD_CACHE[key] = ""
    return _BD_CACHE[key]


def get_available_brands() -> list:
    idx = _get_kit_index()
    return sorted(set(k.split("|")[0] for k in idx if k.split("|")[0]))


def get_kit_types_for_brand(brand: str) -> list:
    idx = _get_kit_index()
    return sorted(set(k.split("|")[1] for k in idx if k.startswith(brand + "|")))


def build_system_prompt(brand: str = "", kit_type: str = "") -> str:
    base   = _get_prompt_base()
    brands = get_available_brands()

    if not brand:
        # Fase 1: sin marca ni kit — solo lista marcas
        return (base + "\n\n---\n\n## MARCAS DISPONIBLES\n\n"
                + "\n".join(f"- {b}" for b in brands) + "\n")

    if not kit_type:
        # Fase 2: marca seleccionada, sin tipo de kit
        kits = get_kit_types_for_brand(brand)
        return (base + "\n\n---\n\n"
                + f"## MARCA: {brand}\n\n"
                + "## TIPOS DE KIT DISPONIBLES\n\n"
                + "\n".join(f"- {k}" for k in kits) + "\n")

    # Fase 3: marca + kit — carga la BD específica
    bd_csv = _get_bd(brand, kit_type)
    return (base + "\n\n---\n\n"
            + f"## BASE DE DATOS — {brand} · {kit_type}\n\n"
            + "```csv\n" + bd_csv + "\n```\n")


def _client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def chat(messages: list, brand: str = "", kit_type: str = "") -> str:
    r = _client().messages.create(
        model=MODEL, max_tokens=2048,
        system=build_system_prompt(brand, kit_type),
        messages=messages)
    return r.content[0].text


def chat_with_image(messages: list, image_data: bytes,
                    media_type: str = "image/jpeg",
                    brand: str = "", kit_type: str = "") -> str:
    b64  = base64.standard_b64encode(image_data).decode("utf-8")
    msgs = list(messages)
    txt  = msgs[-1]["content"] if msgs else ""
    msgs[-1] = {"role": "user", "content": [
        {"type": "image",
         "source": {"type": "base64", "media_type": media_type, "data": b64}},
        {"type": "text", "text": txt},
    ]}
    r = _client().messages.create(
        model=MODEL, max_tokens=2048,
        system=build_system_prompt(brand, kit_type),
        messages=msgs)
    return r.content[0].text
