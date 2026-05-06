import anthropic
import base64
import json
import os
from pathlib import Path

MODEL = "claude-sonnet-4-5"
BASE  = Path(__file__).parent

_PROMPT_CACHE   = None   # prompt base (sin BD)
_BD_CACHE       = {}     # cache por marca: {brand: csv_text}
_INDEX_CACHE    = None   # brand → filename


def _get_brand_index() -> dict:
    global _INDEX_CACHE
    if _INDEX_CACHE is None:
        _INDEX_CACHE = json.loads(
            (BASE / "brand_index.json").read_text(encoding="utf-8"))
    return _INDEX_CACHE


def _get_prompt_base() -> str:
    global _PROMPT_CACHE
    if _PROMPT_CACHE is None:
        _PROMPT_CACHE = (BASE / "prompt_selector_kits_v10.md").read_text(encoding="utf-8")
    return _PROMPT_CACHE


def _get_bd_for_brand(brand: str) -> str:
    """Carga el CSV de la marca desde bd_brands/. Cacheado en memoria."""
    if brand not in _BD_CACHE:
        idx = _get_brand_index()
        fname = idx.get(brand, "")
        if fname:
            csv_path = BASE / "bd_brands" / fname
            _BD_CACHE[brand] = csv_path.read_text(encoding="utf-8")
        else:
            _BD_CACHE[brand] = ""
    return _BD_CACHE[brand]


def build_system_prompt(brand: str = "") -> str:
    """
    Sin marca: solo el prompt base + lista de marcas disponibles.
    Con marca: prompt base + BD completa de esa marca.
    """
    base = _get_prompt_base()
    brands = sorted(_get_brand_index().keys())

    if not brand:
        brand_list = "\n".join(f"- {b}" for b in brands if b)
        return (base
                + "\n\n---\n\n"
                + "## MARCAS DISPONIBLES EN LA BASE DE DATOS\n\n"
                + brand_list + "\n")
    else:
        bd_csv = _get_bd_for_brand(brand)
        return (base
                + "\n\n---\n\n"
                + f"## BASE DE DATOS — {brand}\n\n```csv\n"
                + bd_csv + "\n```\n")


def _client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def chat(messages: list, brand: str = "") -> str:
    r = _client().messages.create(
        model=MODEL, max_tokens=2048,
        system=build_system_prompt(brand),
        messages=messages)
    return r.content[0].text


def chat_with_image(messages: list, image_data: bytes,
                    media_type: str = "image/jpeg", brand: str = "") -> str:
    b64  = base64.standard_b64encode(image_data).decode("utf-8")
    msgs = list(messages)
    txt  = msgs[-1]["content"] if msgs else ""
    msgs[-1] = {"role": "user", "content": [
        {"type": "image", "source": {"type": "base64",
                                     "media_type": media_type, "data": b64}},
        {"type": "text", "text": txt},
    ]}
    r = _client().messages.create(
        model=MODEL, max_tokens=2048,
        system=build_system_prompt(brand),
        messages=msgs)
    return r.content[0].text


def get_available_brands() -> list:
    return sorted(b for b in _get_brand_index().keys() if b)
