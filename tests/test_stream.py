from unittest.mock import patch, MagicMock, call
import json


@patch("commands.stream.edit_message")
@patch("commands.stream.send_message_and_get_id", return_value=100)
@patch("commands.stream.requests.post")
def test_stream_ollama_yields_tokens(mock_post, mock_send, mock_edit):
    from commands.stream import stream_ollama

    chunks = [
        json.dumps({"message": {"content": "Hello"}, "done": False}),
        json.dumps({"message": {"content": " world"}, "done": False}),
        json.dumps({"message": {"content": ""}, "done": True, "prompt_eval_count": 10, "eval_count": 5}),
    ]

    mock_response = MagicMock()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_response.raise_for_status = MagicMock()
    mock_response.iter_lines.return_value = [line.encode() for line in chunks]
    mock_post.return_value = mock_response

    tokens = list(stream_ollama([{"role": "user", "content": "hi"}]))

    assert tokens[0] == "Hello"
    assert tokens[1] == " world"
    assert tokens[2]["done"] is True
    assert tokens[2]["prompt_eval_count"] == 10


@patch("commands.stream.time")
@patch("commands.stream.edit_message", return_value=100)
@patch("commands.stream.send_message_and_get_id", return_value=100)
@patch("commands.stream.stream_ollama")
def test_stream_to_telegram_sends_and_edits(mock_stream, mock_send, mock_edit, mock_time):
    from commands.stream import stream_to_telegram

    mock_time.monotonic.side_effect = [0, 0, 2.0, 3.0]  # Force edits via time progression
    mock_stream.return_value = iter([
        "Hello",
        " world",
        {"done": True, "prompt_eval_count": 10, "eval_count": 5},
    ])

    text, prompt_tokens, comp_tokens = stream_to_telegram(123, [{"role": "user", "content": "hi"}])

    assert text == "Hello world"
    assert prompt_tokens == 10
    assert comp_tokens == 5
    mock_send.assert_called_once_with(123, "Thinking...")


@patch("commands.stream.edit_message", return_value=100)
@patch("commands.stream.send_message_and_get_id", return_value=100)
@patch("commands.stream.stream_ollama")
def test_stream_to_telegram_empty_response(mock_stream, mock_send, mock_edit):
    from commands.stream import stream_to_telegram

    mock_stream.return_value = iter([
        {"done": True, "prompt_eval_count": 0, "eval_count": 0},
    ])

    text, prompt_tokens, comp_tokens = stream_to_telegram(123, [])

    assert text == ""
    # Should edit with "No response generated."
    mock_edit.assert_called_with(123, 100, "No response generated.")
