from bot import send_message


def handle_start(chat_id, args):
    send_message(chat_id, "Hello! I'm your utility bot. Type /help to see what I can do.")
