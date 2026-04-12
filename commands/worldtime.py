from datetime import datetime
from zoneinfo import ZoneInfo
from bot import send_message

ZONES = {
    "IST": "Asia/Kolkata",
    "UTC": "UTC",
    "EST": "America/New_York",
    "PST": "America/Los_Angeles",
    "GMT": "Europe/London",
    "CET": "Europe/Berlin",
    "JST": "Asia/Tokyo",
    "AEST": "Australia/Sydney",
}


def handle_worldtime(chat_id, args, silent=False):
    lines = []
    for label, tz in ZONES.items():
        now = datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"{label}: {now}")
    result = "\n".join(lines)
    if silent:
        return result
    send_message(chat_id, result)
