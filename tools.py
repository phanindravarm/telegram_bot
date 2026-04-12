"""Tool definitions for Ollama function calling and tool execution."""

from commands import COMMANDS

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name to get weather for",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "joke",
            "description": "Get a random joke",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "time",
            "description": "Get the current time in IST",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "worldtime",
            "description": "Get current time across different timezones",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Optional city name (ignored, shows all zones)",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remind",
            "description": "Set a reminder for a specified number of minutes from now",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes": {
                        "type": "number",
                        "description": "Number of minutes from now",
                    },
                    "text": {
                        "type": "string",
                        "description": "The reminder message",
                    },
                },
                "required": ["minutes", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize",
            "description": "Summarize a web page given its URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to summarize",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query",
            "description": "Search and answer questions from the user's indexed knowledge base",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to search for",
                    }
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask",
            "description": "Ask the AI assistant a general question",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask",
                    }
                },
                "required": ["question"],
            },
        },
    },
]

# Maps tool name -> command key
_TOOL_TO_COMMAND = {
    "weather": "/weather",
    "joke": "/joke",
    "time": "/time",
    "worldtime": "/worldtime",
    "remind": "/remind",
    "summarize": "/summarize",
    "query": "/query",
    "ask": "/ask",
}


def format_args(tool_name, args_dict):
    """Convert structured args dict to the string format each handler expects."""
    if tool_name == "weather":
        return args_dict.get("city", "")
    elif tool_name == "joke":
        return ""
    elif tool_name == "time":
        return ""
    elif tool_name == "worldtime":
        return args_dict.get("city", "")
    elif tool_name == "remind":
        minutes = args_dict.get("minutes", 0)
        text = args_dict.get("text", "")
        return f"{minutes} {text}"
    elif tool_name == "summarize":
        return args_dict.get("url", "")
    elif tool_name == "query":
        return args_dict.get("question", "")
    elif tool_name == "ask":
        return args_dict.get("question", "")
    return str(args_dict)


def execute_tool(tool_name, args_dict, chat_id, silent=False):
    """Look up handler, format args, call handler. Returns result string if silent."""
    cmd_key = _TOOL_TO_COMMAND.get(tool_name)
    if not cmd_key:
        msg = f"Unknown tool: {tool_name}"
        if silent:
            return msg
        from bot import send_message
        send_message(chat_id, msg)
        return None

    handler = COMMANDS.get(cmd_key)
    if not handler:
        msg = f"Handler not found for {tool_name}"
        if silent:
            return msg
        from bot import send_message
        send_message(chat_id, msg)
        return None

    args_str = format_args(tool_name, args_dict)
    return handler(chat_id, args_str, silent=silent)


def get_tool_definitions():
    """Return the list of tool definitions for Ollama."""
    return TOOL_DEFINITIONS
