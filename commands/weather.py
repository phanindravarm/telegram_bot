import requests
from bot import send_message


def handle_weather(chat_id, args, silent=False):
    if not args:
        msg = "Usage: /weather <city>"
        if silent:
            return msg
        send_message(chat_id, msg)
        return
    try:
        r = requests.get(f"https://wttr.in/{args}?format=3", timeout=5)
        result = r.text.strip()
        if silent:
            return result
        send_message(chat_id, result)
    except Exception:
        msg = "Could not fetch weather. Try again later."
        if silent:
            return msg
        send_message(chat_id, msg)
