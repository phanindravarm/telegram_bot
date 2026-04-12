import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text})


def send_message_and_get_id(chat_id, text):
    """Send a message and return its message_id for later editing."""
    r = requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text})
    r.raise_for_status()
    return r.json()["result"]["message_id"]


def edit_message(chat_id, message_id, text):
    """Edit an existing message. Handles 4096-char Telegram limit."""
    if len(text) <= 4096:
        requests.post(
            f"{TELEGRAM_API}/editMessageText",
            json={"chat_id": chat_id, "message_id": message_id, "text": text},
        )
        return message_id
    # Text exceeds limit — truncate edit and send overflow as new message
    requests.post(
        f"{TELEGRAM_API}/editMessageText",
        json={"chat_id": chat_id, "message_id": message_id, "text": text[:4096]},
    )
    overflow = text[4096:]
    new_id = send_message_and_get_id(chat_id, overflow)
    return new_id


def get_file_url(file_id):
    """Get a downloadable URL for a Telegram file by its file_id."""
    r = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
    r.raise_for_status()
    file_path = r.json()["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
