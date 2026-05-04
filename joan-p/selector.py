import anthropic
import pandas as pd
import io
import base64
import os
from pathlib import Path


# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
EXCEL_PATH = BASE_DIR / "bbdd_kits_v8.xlsx"
PROMPT_PATH = BASE_DIR / "prompt_selector_kits_v10.md"

# ── Model ─────────────────────────────────────────────────────────────────────
MODEL = "claude-sonnet-4-20250514"


# ── Load resources (cached at module level) ───────────────────────────────────
def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _load_excel_as_b64() -> str:
    """Read the Excel file and return it as a base64-encoded string."""
    return base64.standard_b64encode(EXCEL_PATH.read_bytes()).decode("utf-8")


def _load_excel_as_csv_text() -> str:
    """
    Convert the Excel to a compact CSV string so it can be injected into the
    system prompt as plain text (token-efficient, no vision needed).
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name=0, dtype=str)
    df = df.fillna("")
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


# Pre-load once when the module is imported
_SYSTEM_PROMPT_BASE = _load_prompt()
_EXCEL_CSV          = _load_excel_as_csv_text()

# Build the full system prompt: instructions + data
SYSTEM_PROMPT = (
    _SYSTEM_PROMPT_BASE
    + "\n\n---\n\n## BASE DE DATOS — bbdd_kits_v8 (CSV)\n\n"
    + "```csv\n"
    + _EXCEL_CSV
    + "\n```\n"
)


# ── Anthropic client ──────────────────────────────────────────────────────────
def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)


# ── Public API ────────────────────────────────────────────────────────────────
def chat(messages: list[dict]) -> str:
    """
    Send the conversation history to Claude and return the assistant reply.

    Parameters
    ----------
    messages : list of {"role": "user"|"assistant", "content": str}
        Full conversation history (NOT including the system prompt).

    Returns
    -------
    str
        The assistant's text reply.
    """
    client = _get_client()

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    # Extract the text block from the response
    return response.content[0].text


def chat_with_image(messages: list[dict], image_data: bytes, media_type: str = "image/jpeg") -> str:
    """
    Send a conversation with an image attachment (e.g. a vehicle registration document).

    Parameters
    ----------
    messages      : conversation history (last user message should NOT include the image yet)
    image_data    : raw bytes of the image
    media_type    : MIME type of the image

    Returns
    -------
    str  – assistant reply
    """
    client = _get_client()

    # Inject image into the last user turn
    img_b64 = base64.standard_b64encode(image_data).decode("utf-8")

    # Build a copy of messages with the image appended to the last user message
    msgs = list(messages)
    last_user_text = msgs[-1]["content"] if msgs else ""
    msgs[-1] = {
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": img_b64,
                },
            },
            {"type": "text", "text": last_user_text},
        ],
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=msgs,
    )

    return response.content[0].text
