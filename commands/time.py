from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from bot import send_message


def handle_time(chat_id, args, silent=False):
    now = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST")
    result = f"Current time: {now}"
    if silent:
        return result
    send_message(chat_id, result)
