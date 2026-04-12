import os
import base64
import requests
from openai import OpenAI
from bot import send_message, get_file_url
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

HF_MODEL = "meta-llama/Llama-4-Scout-17B-16E-Instruct:groq"
DEFAULT_PROMPT = "Describe this image in detail."


def handle_vision(chat_id, file_id, caption=""):
    if not HF_TOKEN:
        send_message(chat_id, "Bot is not configured. Please set the HF_TOKEN.")
        return

    prompt = caption.strip() if caption.strip() else DEFAULT_PROMPT

    try:
        file_url = get_file_url(file_id)
        resp = requests.get(file_url, timeout=15)
        resp.raise_for_status()
        image_data = base64.b64encode(resp.content).decode("utf-8")
    except Exception:
        send_message(chat_id, "Could not download the photo. Please try again.")
        return

    try:
        completion = client.chat.completions.create(
            model=HF_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1024,
        )

        text = completion.choices[0].message.content
        send_message(chat_id, text)

    except Exception as e:
        send_message(chat_id, f"Could not analyze the image. Error: {e}")