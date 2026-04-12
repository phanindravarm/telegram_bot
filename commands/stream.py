import json
import time
import requests

from bot import send_message_and_get_id, edit_message
from commands.ask_config import OLLAMA_BASE_URL, MODEL

# Minimum interval between Telegram edits (seconds)
EDIT_THROTTLE = 1.0


def stream_ollama(messages, model=None):
    """Generator yielding tokens from Ollama streaming response."""
    payload = {
        "model": model or MODEL,
        "messages": messages,
        "stream": True,
    }
    with requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        stream=True,
        timeout=120,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            token = data.get("message", {}).get("content", "")
            if token:
                yield token
            if data.get("done"):
                # Yield token usage info as final item
                yield {
                    "done": True,
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0),
                }
                return


def stream_to_telegram(chat_id, messages, model=None):
    """Stream Ollama response to Telegram with progressive message editing.

    Returns (final_text, prompt_tokens, completion_tokens).
    """
    message_id = send_message_and_get_id(chat_id, "Thinking...")
    accumulated = ""
    last_edit = 0
    prompt_tokens = 0
    completion_tokens = 0

    for token in stream_ollama(messages, model=model):
        if isinstance(token, dict) and token.get("done"):
            prompt_tokens = token.get("prompt_eval_count", 0)
            completion_tokens = token.get("eval_count", 0)
            break

        accumulated += token
        now = time.monotonic()
        if now - last_edit >= EDIT_THROTTLE:
            message_id = edit_message(chat_id, message_id, accumulated)
            last_edit = now

    # Final edit with complete text
    if accumulated:
        edit_message(chat_id, message_id, accumulated)
    else:
        edit_message(chat_id, message_id, "No response generated.")

    return accumulated, prompt_tokens, completion_tokens
