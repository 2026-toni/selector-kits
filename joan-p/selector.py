import anthropic
import base64
import os
from pathlib import Path

MODEL = "claude-sonnet-4-5"
BASE  = Path(__file__).parent

# Ratio de tokens medido en producción (chars reales / tokens reales)
_RATIO = 2.6394
# Límite seguro: 185K tokens (15K de margen sobre el límite de 200K)
_MAX_CHARS = int(185000 * _RATIO)

_CACHE = None


def _build_system_prompt() -> str:
    prompt = (BASE / "prompt_selector_kits_v10.md").read_text(encoding="utf-8")
    bd_sel = (BASE / "bd_sel.csv").read_text(encoding="utf-8")

    # Recortar bd_sel si es necesario para no superar el límite
    prompt_chars = len(prompt)
    overhead = 60  # chars del separador y cabecera CSV
    max_bd_chars = _MAX_CHARS - prompt_chars - overhead
    if len(bd_sel) > max_bd_chars:
        # Cortar por líneas completas (no romper filas CSV)
        lines = bd_sel.splitlines()
        header = lines[0]
        rows = lines[1:]
        kept = [header]
        used = len(header)
        for row in rows:
            if used + len(row) + 1 > max_bd_chars:
                break
            kept.append(row)
            used += len(row) + 1
        bd_sel = "\n".join(kept)

    return (
        prompt
        + "\n\n---\n\n"
        + "## BASE DE DATOS\n\n```csv\n"
        + bd_sel
        + "\n```\n"
    )


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
    txt = msgs[-1]["content"] if msgs else ""
    msgs[-1] = {"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
        {"type": "text", "text": txt}
    ]}
    r = _client().messages.create(
        model=MODEL, max_tokens=2048,
        system=get_system_prompt(), messages=msgs)
    return r.content[0].text
