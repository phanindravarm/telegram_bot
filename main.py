import asyncio
import logging
import traceback
from datetime import datetime, timezone

from fastapi import FastAPI, Request
import os
from dotenv import load_dotenv
import ngrok
import uvicorn

load_dotenv()

from bot import send_message, TELEGRAM_API
from commands import COMMANDS, PHOTO_COMMANDS, DOCUMENT_COMMANDS

import requests

logger = logging.getLogger(__name__)

app = FastAPI()


def parse_caption(caption):
    """Extract /command and remaining args from a caption string."""
    caption = caption.strip()
    if not caption.startswith("/"):
        return None, caption
    parts = caption.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    return cmd, args


def set_webhook(url):
    r = requests.post(f"{TELEGRAM_API}/setWebhook", json={"url": f"{url}/webhook"})
    logger.info("Webhook set: %s", r.json())


@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        if "message" not in data:
            return "OK"

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if "photo" in data["message"]:
            file_id = data["message"]["photo"][-1]["file_id"]
            caption = data["message"].get("caption", "")
            cmd, caption_args = parse_caption(caption)
            handler = PHOTO_COMMANDS.get(cmd or "/vision")
            if handler:
                await asyncio.to_thread(handler, chat_id, file_id, caption_args)
            return "OK"

        if "document" in data["message"]:
            doc = data["message"]["document"]
            file_id = doc["file_id"]
            file_name = doc.get("file_name", "")
            mime_type = doc.get("mime_type", "")
            caption = data["message"].get("caption", "")
            cmd, _ = parse_caption(caption)
            if cmd:
                handler = DOCUMENT_COMMANDS.get(cmd)
            elif not caption:
                handler = DOCUMENT_COMMANDS.get("/summarize")
            else:
                handler = None
            if handler:
                await asyncio.to_thread(handler, chat_id, file_id, file_name, mime_type)
            else:
                await asyncio.to_thread(send_message, chat_id, "Send a document with /summarize or /upload caption.")
            return "OK"

        if not text:
            return "OK"

        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            command = parts[0].lower().split("@")[0]
            args = parts[1] if len(parts) > 1 else ""

            handler = COMMANDS.get(command)
            if handler:
                await asyncio.to_thread(handler, chat_id, args)
            else:
                await asyncio.to_thread(send_message, chat_id, "Unknown command. Try /help for available commands.")
        else:
            # Plain text → AI agent (planner + ReAct loop with tool calling).
            # Falls back to the cosine-similarity router if Ollama is unreachable.
            from agent import run_agent

            agent_result = await asyncio.to_thread(run_agent, chat_id, text)
            if agent_result is None:
                from router import classify_intent
                result = classify_intent(text)
                if result:
                    intent, _, args = result
                    handler = COMMANDS.get(intent)
                    if handler:
                        await asyncio.to_thread(handler, chat_id, args)
                    else:
                        await asyncio.to_thread(send_message, chat_id, "Try /help for available commands.")
                else:
                    ask_handler = COMMANDS.get("/ask")
                    if ask_handler:
                        await asyncio.to_thread(ask_handler, chat_id, text)
                    else:
                        await asyncio.to_thread(send_message, chat_id, "Try /help for available commands.")
    except Exception as e:
        logger.error("Error handling update: %s\n%s", e, traceback.format_exc())

    return "OK"


def reschedule_pending_reminders():
    from db import get_pending_reminders
    from commands.remind import schedule_reminder

    reminders = get_pending_reminders()
    now = datetime.now(timezone.utc)
    for reminder_id, chat_id, reminder_text, trigger_time_str in reminders:
        trigger_time = datetime.fromisoformat(trigger_time_str).replace(tzinfo=timezone.utc)
        delay = (trigger_time - now).total_seconds()
        schedule_reminder(reminder_id, chat_id, reminder_text, delay)
    if reminders:
        logger.info("Rescheduled %d pending reminder(s).", len(reminders))


if __name__ == "__main__":
    from db import init_db

    logging.basicConfig(level=logging.INFO)
    listener = ngrok.forward(3000, authtoken_from_env=True)
    public_url = listener.url()
    logger.info("ngrok tunnel: %s", public_url)
    set_webhook(public_url)
    init_db()
    reschedule_pending_reminders()
    try:
        uvicorn.run(app, host="0.0.0.0", port=3000)
    finally:
        if public_url:
            ngrok.disconnect(public_url)
        ngrok.kill()
        logger.info("ngrok stopped successfully")
