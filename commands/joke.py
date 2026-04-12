import requests
from bot import send_message


def handle_joke(chat_id, args, silent=False):
    try:
        r = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=5)
        joke = r.json()
        result = f"{joke['setup']}\n\n{joke['punchline']}"
        if silent:
            return result
        send_message(chat_id, result)
    except Exception as e :
        print("Error in handle_joke : ", e)
        msg = "Could not fetch a joke. Try again later."
        if silent:
            return msg
        send_message(chat_id, msg)
