import anthropic
import base64
import os
from pathlib import Path

MODEL = "claude-sonnet-4-5"
BASE  = Path(__file__).parent

_CACHE = None


def _build_system_prompt() -> str:
    """
    Construye el system prompt recortando bd_sel.csv fila a fila hasta que
    el conteo EXACTO de tokens de la API quede por debajo de 195000.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    prompt   = (BASE / "prompt_selector_kits_v10.md").read_text(encoding="utf-8")
    bd_lines = (BASE / "bd_sel.csv").read_text(encoding="utf-8").splitlines()

    header = bd_lines[0]
    rows   = bd_lines[1:]

    # Empezar con todas las filas e ir quitando de 50 en 50 hasta caber
    kept = list(rows)
    while True:
        csv_text   = header + "\n" + "\n".join(kept)
        system_txt = (prompt + "\n\n---\n\n## BASE DE DATOS\n\n```csv\n"
                      + csv_text + "\n```\n")

        # Contar tokens exactos con la API (no cobra, es gratis)
        resp = client.messages.count_tokens(
            model=MODEL,
            system=system_txt,
            messages=[{"role": "user", "content": "x"}],
        )
        total = resp.input_tokens

        if total <= 195000:
            return system_txt   # ✅ cabe

        # Quitar 50 filas del final y reintentar
        if len(kept) <= 50:
            # Caso extremo: devolver aunque sea grande
            return system_txt
        kept = kept[:-50]


def get_system_prompt() -> str:
    global _CACHE
    if _CACHE is None:
        _CACHE = _build_system_prompt()
    return _CACHE


def _client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def chat(messages: list) -> str:
    r = _client().messages.create(
        model=MODEL, max_tokens=2048,
        system=get_system_prompt(), messages=messages)
    return r.content[0].text


def chat_with_image(messages: list, image_data: bytes, media_type: str = "image/jpeg") -> str:
    b64 = base64.standard_b64encode(image_data).decode("utf-8")
    msgs = list(messages)
    txt  = msgs[-1]["content"] if msgs else ""
    msgs[-1] = {"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
        {"type": "text", "text": txt},
    ]}
    r = _client().messages.create(
        model=MODEL, max_tokens=2048,
        system=get_system_prompt(), messages=msgs)
    return r.content[0].text
