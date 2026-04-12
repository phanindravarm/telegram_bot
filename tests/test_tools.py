from unittest.mock import patch, MagicMock


def test_get_tool_definitions_returns_list():
    from tools import get_tool_definitions

    defs = get_tool_definitions()
    assert isinstance(defs, list)
    assert len(defs) == 8

    names = [d["function"]["name"] for d in defs]
    assert "weather" in names
    assert "joke" in names
    assert "time" in names
    assert "worldtime" in names
    assert "remind" in names
    assert "summarize" in names
    assert "query" in names
    assert "ask" in names


def test_format_args_weather():
    from tools import format_args

    assert format_args("weather", {"city": "London"}) == "London"


def test_format_args_joke():
    from tools import format_args

    assert format_args("joke", {}) == ""


def test_format_args_remind():
    from tools import format_args

    result = format_args("remind", {"minutes": 5, "text": "drink water"})
    assert result == "5 drink water"


def test_format_args_summarize():
    from tools import format_args

    assert format_args("summarize", {"url": "https://example.com"}) == "https://example.com"


def test_format_args_query():
    from tools import format_args

    assert format_args("query", {"question": "what is AI?"}) == "what is AI?"


def test_format_args_ask():
    from tools import format_args

    assert format_args("ask", {"question": "hello"}) == "hello"


@patch("tools.COMMANDS")
def test_execute_tool_calls_handler_silent(mock_commands):
    from tools import execute_tool

    mock_handler = MagicMock(return_value="London: +15°C")
    mock_commands.get.return_value = mock_handler

    result = execute_tool("weather", {"city": "London"}, chat_id=123, silent=True)

    assert result == "London: +15°C"
    mock_handler.assert_called_once_with(123, "London", silent=True)


@patch("tools.COMMANDS")
def test_execute_tool_calls_handler_not_silent(mock_commands):
    from tools import execute_tool

    mock_handler = MagicMock(return_value=None)
    mock_commands.get.return_value = mock_handler

    result = execute_tool("weather", {"city": "London"}, chat_id=123, silent=False)

    mock_handler.assert_called_once_with(123, "London", silent=False)


def test_execute_tool_unknown_tool():
    from tools import execute_tool

    result = execute_tool("unknown_tool", {}, chat_id=123, silent=True)
    assert "Unknown tool" in result


def test_tool_definitions_have_required_fields():
    from tools import get_tool_definitions

    for tool in get_tool_definitions():
        assert "type" in tool
        assert tool["type"] == "function"
        func = tool["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func
