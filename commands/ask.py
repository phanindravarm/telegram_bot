import requests
from bot import send_message
from db import save_message, get_history, clear_history, log_token_usage
from commands.stream import stream_to_telegram
from commands.ask_config import (
    SYSTEM_PROMPT,
    MODEL,
    OLLAMA_BASE_URL,
    MAX_CONTEXT_TOKENS,
    MAX_RESPONSE_TOKENS,
    CHARS_PER_TOKEN,
    MAX_HISTORY_MESSAGES,
)


def estimate_tokens(text):
    return max(1, len(text) // CHARS_PER_TOKEN)


def truncate_history(messages, budget):
    """Drop oldest messages until total token estimate fits within budget."""
    total = sum(m[2] for m in messages)
    trimmed = list(messages)
    while total > budget and len(trimmed) > 1:
        total -= trimmed[0][2]
        trimmed.pop(0)
    return trimmed


def build_messages(chat_id, new_message):
    history = get_history(chat_id, limit=MAX_HISTORY_MESSAGES)
    new_tokens = estimate_tokens(new_message)
    budget = MAX_CONTEXT_TOKENS - new_tokens
    history = truncate_history(history, budget)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for role, content, _tokens in history:
        r = "assistant" if role == "model" else role
        messages.append({"role": r, "content": content})
    messages.append({"role": "user", "content": new_message})
    return messages


def call_ollama(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
    }
    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def call_ollama_with_tools(messages, tools, model=None):
    """Call Ollama with tool/function definitions."""
    payload = {
        "model": model or MODEL,
        "messages": messages,
        "tools": tools,
        "stream": False,
    }
    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def extract_response(data):
    text = data["message"]["content"]
    prompt_tokens = data.get("prompt_eval_count", 0)
    completion_tokens = data.get("eval_count", 0)
    return text, prompt_tokens, completion_tokens


def handle_ask(chat_id, args, silent=False):
    if not args:
        msg = "Usage: /ask <question>"
        if silent:
            return msg
        send_message(chat_id, msg)
        return

    try:
        messages = build_messages(chat_id, args)

        if silent:
            # Non-streaming for silent mode (agent use)
            data = call_ollama(messages)
            text, prompt_tokens, completion_tokens = extract_response(data)
        else:
            text, prompt_tokens, completion_tokens = stream_to_telegram(
                chat_id, messages
            )

        user_token_est = estimate_tokens(args)
        model_token_est = estimate_tokens(text)
        save_message(chat_id, "user", args, user_token_est)
        save_message(chat_id, "model", text, model_token_est)

        log_token_usage(chat_id, prompt_tokens, completion_tokens)

        if silent:
            return text
    except Exception:
        msg = "Could not get a response. Try again later."
        if silent:
            return msg
        send_message(chat_id, msg)
