import requests
from bot import send_message, get_file_url
from commands.ask_config import MODEL, OLLAMA_BASE_URL
from commands.document_utils import extract_text_from_file
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

SUMMARIZE_PROMPT = """
Read the following web page content and explain it naturally, like a person would.

Write in a slightly informal, human tone — not robotic or overly structured.
Avoid generic phrases and avoid sounding like a report.

Focus on what actually matters:
- What is this about?
- What’s interesting or important?
- Any useful examples or details

Make it feel like you’re telling someone what you just read.

Keep it under 300 words.
Plain text only.
"""

def fetch_page_text(url, max_chars=10000):
    """Fetch a webpage and return cleaned visible text."""

    # Setup session with retries
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    try:
        # Request page
        resp = session.get(
            url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        resp.raise_for_status()

        html = resp.text

        # Clean HTML → extract text
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text[:max_chars]

    except requests.exceptions.RequestException as e:
        return f"Error fetching page: {e}"


def _summarize_text(chat_id, text, silent=False):
    """Send text to Ollama for summarization and reply to the user."""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": SUMMARIZE_PROMPT + text}],
        "stream": False,
    }

    try:
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        summary = r.json()["message"]["content"]
        if silent:
            return summary
        send_message(chat_id, summary)
    except Exception as e:
        print("Error in summary : ", e)
        msg = "Could not generate a summary. Try again later."
        if silent:
            return msg
        send_message(chat_id, msg)


def handle_summarize(chat_id, args, silent=False):
    url = args.strip()
    if not url:
        msg = "Usage: /summarize <url>"
        if silent:
            return msg
        send_message(chat_id, msg)
        return

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        page_text = fetch_page_text(url)
    except Exception:
        msg = "Could not fetch that URL. Please check and try again."
        if silent:
            return msg
        send_message(chat_id, msg)
        return

    if len(page_text) < 50:
        msg = "Could not extract enough text from that page."
        if silent:
            return msg
        send_message(chat_id, msg)
        return

    return _summarize_text(chat_id, page_text, silent=silent)


def handle_summarize_document(chat_id, file_id, file_name, mime_type):
    """Handle a document attachment sent with /summarize."""

    try:
        file_url = get_file_url(file_id)
        resp = requests.get(file_url, timeout=30)
        resp.raise_for_status()
        file_bytes = resp.content
    except Exception:
        send_message(chat_id, "Could not download the file. Please try again.")
        return

    text, error = extract_text_from_file(file_bytes, mime_type, file_name)
    if error:
        send_message(chat_id, error)
        return

    _summarize_text(chat_id, text)
