import threading
from datetime import datetime, timedelta, timezone

from bot import send_message
from db import save_reminder, delete_reminder


def _fire_reminder(reminder_id, chat_id, reminder_text):
    send_message(chat_id, f"Reminder: {reminder_text}")
    delete_reminder(reminder_id)


def schedule_reminder(reminder_id, chat_id, reminder_text, delay_seconds):
    if delay_seconds <= 0:
        _fire_reminder(reminder_id, chat_id, reminder_text)
    else:
        threading.Timer(
            delay_seconds, _fire_reminder, args=(reminder_id, chat_id, reminder_text)
        ).start()


def handle_remind(chat_id, args, silent=False):
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        msg = "Usage: /remind <minutes> <message>"
        if silent:
            return msg
        send_message(chat_id, msg)
        return
    try:
        minutes = float(parts[0])
        reminder_text = parts[1]

        if minutes < 0:
            msg = "Minutes must be positive"
            if silent:
                return msg
            send_message(chat_id, msg)
            return

        trigger_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        reminder_id = save_reminder(chat_id, reminder_text, trigger_time)
        schedule_reminder(reminder_id, chat_id, reminder_text, minutes * 60)
        result = f"Reminder set for {minutes} minute(s)."
        if silent:
            return result
        send_message(chat_id, result)
    except ValueError:
        msg = "Minutes must be a number. Usage: /remind <minutes> <message>"
        if silent:
            return msg
        send_message(chat_id, msg)
