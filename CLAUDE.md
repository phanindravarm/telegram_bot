# Telegram Bot

Python/FastAPI Telegram bot using ngrok for webhook tunneling and SQLite for persistence.

## Setup

```bash
source env/bin/activate
pip install -r requirements.txt
python main.py
```

### Required env vars (in `.env`)
- `BOT_TOKEN` — Telegram bot token
- `NGROK_AUTHTOKEN` — ngrok auth token
- `HF_TOKEN` — Hugging Face API token (used by /vision)

### Optional env vars
- `OLLAMA_BASE_URL` — Ollama server URL (defaults to `http://localhost:11434`)
- `TOOL_USE_MODEL` — Ollama model for tool calling/agent (defaults to `llama3.1`)

### Ollama setup
Requires Ollama running locally (`ollama serve`) with models pulled:
- `ollama pull llama3.2` (chat)
- `ollama pull llama3.1` (tool calling/agent)

## Project structure

```
main.py              — FastAPI app, ngrok tunnel, webhook setup, reminder polling
bot.py               — send_message / send_message_and_get_id / edit_message (Telegram HTTP API)
db.py                — SQLite DB: init_db(), _connect(), CRUD for reminders/history/tokens/rag_chunks
router.py            — semantic intent classifier (cosine similarity fallback when Ollama is down)
tools.py             — tool definitions for Ollama function calling + execute_tool()
agent.py             — AI agent: planner → ReAct loop → tool chaining → synthesize
commands/            — one file per bot command; registered in __init__.py
  __init__.py        — imports + COMMANDS / PHOTO_COMMANDS / DOCUMENT_COMMANDS dicts
  ask.py             — AI chat via Ollama (streaming), call_ollama_with_tools
  ask_config.py      — model config, TOOL_USE_MODEL, AGENT_MAX_STEPS
  clear.py           — /clear conversation history
  document_utils.py  — PDF/DOCX/TXT text extraction
  help.py            — /help text listing all commands
  joke.py            — /joke via official-joke-api
  rag.py             — /ingest, /query (hybrid BM25+semantic), /sources, /forget
  remind.py          — /remind with threading.Timer scheduling
  start.py           — /start welcome message
  stream.py          — streaming Ollama responses with Telegram edit-in-place
  summarize.py       — /summarize web pages and documents via Ollama
  time.py            — /time current IST time
  vision.py          — /vision image analysis via Hugging Face
  weather.py         — /weather via wttr.in API
  worldtime.py       — /worldtime across 8 timezones
tests/               — pytest tests, one file per module
```

## AI Agent (plain text routing)

Plain text messages (not starting with `/`) are routed through `agent.py`:

### Planner–Executor architecture
1. **Planner** (`plan_request`) — single LLM call rewrites user input as a numbered action plan (e.g. "1. Call joke(). 2. Call remind(minutes=2, text=<the joke from step 1>).")
2. **Executor** — ReAct loop feeds the plan to `TOOL_USE_MODEL` with tool definitions; executes tool calls via `execute_tool(silent=True)`
3. **Step substitution** (`_substitute_step_refs`) — replaces `<...step N...>` placeholders in tool args with actual results from earlier steps; auto-fills missing `text` for remind
4. **Consumed-result filtering** — intermediate results used as input to later tools (e.g. a joke fed into remind) are hidden from the final user-facing response
5. **Final response** — tool results are sent directly to Telegram (bypasses LLM rephrasing to avoid hallucinated commentary)

### Multi-intent support
- Handles queries like "tell me a joke and what is an agent" → planner decomposes into 2+ steps
- Handles scheduling like "remind me of a joke in 2 mins" → planner chains joke() → remind()
- Falls back to `router.py` cosine-similarity routing if Ollama is unreachable

### Available tools (defined in `tools.py`)
weather, joke, time, worldtime, remind, summarize, query, ask

## RAG (Retrieval-Augmented Generation)

- `/ingest <url>` or upload a document → chunk (500 chars, 50-char overlap) → embed with `all-MiniLM-L6-v2` → store in `rag_chunks`
- `/query <question>` → hybrid search (BM25 + semantic cosine similarity fused with Reciprocal Rank Fusion) → top-5 chunks → Ollama answers from context
- `/sources` — list indexed sources with chunk counts
- `/forget <source>` — delete chunks by source name
- Supported upload formats: PDF, DOCX, TXT

## Streaming

- `/ask` and agent final answers use streaming (edit-in-place with ~1s throttle)
- `commands/stream.py` provides `stream_ollama()` generator and `stream_to_telegram()` helper
- Handles 4096-char Telegram message limit by splitting into new messages

## Legacy intent router (fallback)

`router.py` is kept as a fallback when Ollama is unreachable:
- Uses `sentence-transformers` (`all-MiniLM-L6-v2`) embeddings
- Cosine similarity with 0.45 threshold, 0.05 ambiguity margin

## Adding a new command

1. Create `commands/<name>.py` with `def handle_<name>(chat_id, args):`
2. Import and register in `commands/__init__.py`
3. Add help text line in `commands/help.py`
4. If it should be callable by the agent, add a tool definition in `tools.py`
5. Create `tests/test_<name>.py`
6. Change `tests/test_help` accordingly

## Testing

```bash
source env/bin/activate && pytest tests/ -v
```

## Rules

- Never commit `.env` or `reminders.db`
- All command handlers take `(chat_id, args, silent=False)` as parameters
- When `silent=True`, handlers return result strings instead of sending to Telegram
- Use `bot.send_message(chat_id, text)` to reply
- Use `db._connect()` pattern for database access
