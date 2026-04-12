from bot import send_message
from db import clear_history


def handle_clear(chat_id, args):
    clear_history(chat_id)
    send_message(chat_id, "Conversation history cleared.")
