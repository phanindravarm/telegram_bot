from commands.start import handle_start
from commands.help import handle_help
from commands.weather import handle_weather
from commands.joke import handle_joke
from commands.time import handle_time
from commands.remind import handle_remind
from commands.ask import handle_ask
from commands.clear import handle_clear
from commands.vision import handle_vision
from commands.summarize import handle_summarize, handle_summarize_document
from commands.worldtime import handle_worldtime
from commands.rag import handle_ingest, handle_query, handle_sources, handle_forget, handle_upload_document

COMMANDS = {
    "/start": handle_start,
    "/help": handle_help,
    "/weather": handle_weather,
    "/joke": handle_joke,
    "/time": handle_time,
    "/remind": handle_remind,
    "/ask": handle_ask,
    "/clear": handle_clear,
    "/summarize": handle_summarize,
    "/worldtime": handle_worldtime,
    "/ingest": handle_ingest,
    "/query": handle_query,
    "/sources": handle_sources,
    "/forget": handle_forget,
}

PHOTO_COMMANDS = {
    "/vision": handle_vision,
}

DOCUMENT_COMMANDS = {
    "/upload": handle_upload_document,
    "/summarize": handle_summarize_document,
}
