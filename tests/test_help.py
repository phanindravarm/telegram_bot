from unittest.mock import patch


@patch("commands.help.send_message")
def test_handle_help_lists_all_commands(mock_send):
    from commands.help import handle_help

    handle_help(123, "")

    mock_send.assert_called_once()
    text = mock_send.call_args[0][1]
    for cmd in ["/start", "/help", "/weather", "/joke", "/time", "/remind",
                "/ask", "/clear", "/vision", "/summarize", "/worldtime",
                "/ingest", "/upload", "/query", "/sources", "/forget"]:
        assert cmd in text, f"{cmd} not found in help text"


@patch("commands.help.send_message")
def test_handle_help_sends_to_correct_chat(mock_send):
    from commands.help import handle_help

    handle_help(456, "")

    mock_send.assert_called_once()
    assert mock_send.call_args[0][0] == 456


@patch("commands.help.send_message")
def test_handle_help_ignores_args(mock_send):
    from commands.help import handle_help

    handle_help(123, "some extra args")

    mock_send.assert_called_once()
    text = mock_send.call_args[0][1]
    assert "/help" in text


@patch("commands.help.send_message")
def test_handle_help_includes_natural_language_hint(mock_send):
    from commands.help import handle_help

    handle_help(123, "")

    text = mock_send.call_args[0][1]
    assert "type naturally" in text
