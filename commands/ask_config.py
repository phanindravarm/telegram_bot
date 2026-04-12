import os

SYSTEM_PROMPT = (
    "You are a helpful Telegram bot assistant. "
    "Be concise and direct in your responses. "
    "Use plain text formatting suitable for Telegram messages."
)
MODEL = "llama3.2"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MAX_CONTEXT_TOKENS = 8000
MAX_RESPONSE_TOKENS = 2048
CHARS_PER_TOKEN = 4
MAX_HISTORY_MESSAGES = 50
TOOL_USE_MODEL = os.environ.get("TOOL_USE_MODEL", "llama3.1")
AGENT_MAX_STEPS = 5
