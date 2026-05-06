import anthropic
import base64
import os
from pathlib import Path

MODEL = "claude-sonnet-4-5"
BASE  = Path(__file__).parent
_CACHE = None

def get_system_prompt():
    global _CACHE
    if _CACHE is None:
        prompt = (BASE / "prompt_selector_kits_v10.md").read_text(encoding="utf-8")
        bd_sel = (BASE / "bd_sel.csv").read_text(encoding="utf-8")
        _CACHE = prompt + "\n\n---\n\n## BASE DE DATOS\n\n```csv\n" + bd_sel + "\n```\n"
    return _CACHE

def _client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

def chat(messages: list) -> str:
    r = _client().messages.create(model=MODEL, max_tokens=2048,
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
    r = _client().messages.create(model=MODEL, max_tokens=2048,
        system=get_system_prompt(), messages=msgs)
    return r.content[0].text
