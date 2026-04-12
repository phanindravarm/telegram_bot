from bot import send_message


def handle_help(chat_id, args):
    send_message(chat_id,
        "/start - Welcome message\n"
        "/help - List commands\n"
        "/weather <city> - Current weather\n"
        "/joke - Random joke\n"
        "/time - Current UTC time\n"
        "/remind <minutes> <message> - Set a reminder\n"
        "/ask <question> - Ask AI a question\n"
        "/clear - Clear conversation history\n"
        "/vision - Send a photo to analyze it with AI\n"
        "/summarize <url> / (with attachment) - Summarize a web page, PDF, TXT, or DOCX file\n"
        "/worldtime - Current time across different timezones\n"
        "/ingest <url> - Index a web page into your knowledge base\n"
        "/upload - Send a document with /upload caption to index it\n"
        "/query <question> - Ask a question about your indexed content\n"
        "/sources - List your indexed sources\n"
        "/forget <source> - Remove a source from your knowledge base"
        "\n\nYou can also just type naturally — the AI agent will figure out which tools to use, and can even combine multiple actions in one message!"
    )
