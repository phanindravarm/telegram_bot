from unittest.mock import patch, MagicMock


@patch("commands.ask.send_message")
def test_handle_ask_no_args(mock_send):
    from commands.ask import handle_ask

    handle_ask(123, "")

    mock_send.assert_called_once()
    assert "usage" in mock_send.call_args[0][1].lower()


@patch("commands.ask.log_token_usage")
@patch("commands.ask.save_message")
@patch("commands.ask.get_history", return_value=[])
@patch("commands.ask.stream_to_telegram")
def test_handle_ask_success(mock_stream, mock_get_hist, mock_save, mock_log):
    from commands.ask import handle_ask

    mock_stream.return_value = ("Python is great.", 10, 5)

    handle_ask(123, "What is Python?")

    mock_stream.assert_called_once()


@patch("commands.ask.log_token_usage")
@patch("commands.ask.save_message")
@patch("commands.ask.get_history", return_value=[])
@patch("commands.ask.stream_to_telegram")
def test_handle_ask_saves_to_db(mock_stream, mock_get_hist, mock_save, mock_log):
    from commands.ask import handle_ask

    mock_stream.return_value = ("Answer", 10, 2)

    handle_ask(123, "Question")

    assert mock_save.call_count == 2
    # First call: user message
    assert mock_save.call_args_list[0][0][0] == 123
    assert mock_save.call_args_list[0][0][1] == "user"
    assert mock_save.call_args_list[0][0][2] == "Question"
    # Second call: model response
    assert mock_save.call_args_list[1][0][1] == "model"
    assert mock_save.call_args_list[1][0][2] == "Answer"


@patch("commands.ask.log_token_usage")
@patch("commands.ask.save_message")
@patch("commands.ask.get_history", return_value=[])
@patch("commands.ask.stream_to_telegram")
def test_handle_ask_logs_token_usage(mock_stream, mock_get_hist, mock_save, mock_log):
    from commands.ask import handle_ask

    mock_stream.return_value = ("Hi", 15, 3)

    handle_ask(123, "Hello")

    mock_log.assert_called_once_with(123, 15, 3)


@patch("commands.ask.log_token_usage")
@patch("commands.ask.save_message")
@patch("commands.ask.get_history")
@patch("commands.ask.stream_to_telegram")
def test_handle_ask_success_with_history(mock_stream, mock_get_hist, mock_save, mock_log):
    from commands.ask import handle_ask

    mock_get_hist.return_value = [
        ("user", "Hi", 1),
        ("model", "Hello!", 2),
    ]
    mock_stream.return_value = ("Sure!", 20, 2)

    handle_ask(123, "Tell me more")

    # Verify messages include system + history + new message
    call_args = mock_stream.call_args[0]
    messages = call_args[1]  # second positional arg is messages
    assert len(messages) == 4  # system + 2 history + new
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["content"] == "Tell me more"


def test_handle_ask_system_prompt_included():
    from commands.ask import call_ollama, SYSTEM_PROMPT

    with patch("commands.ask.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "message": {"role": "assistant", "content": "ok"},
        }
        mock_post.return_value = mock_resp

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "hi"},
        ]
        call_ollama(messages)

        payload = mock_post.call_args[1]["json"]
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == SYSTEM_PROMPT
        assert payload["stream"] is False


def test_handle_ask_truncates_long_history():
    from commands.ask import truncate_history

    # Create history that exceeds budget
    messages = [
        ("user", "a" * 4000, 1000),
        ("model", "b" * 4000, 1000),
        ("user", "c" * 4000, 1000),
        ("model", "d" * 4000, 1000),
    ]

    result = truncate_history(messages, budget=2500)

    total = sum(m[2] for m in result)
    assert total <= 2500
    # Should keep the newest messages
    assert result[-1] == messages[-1]


@patch("commands.ask.send_message")
@patch("commands.ask.stream_to_telegram", side_effect=Exception("timeout"))
@patch("commands.ask.get_history", return_value=[])
def test_handle_ask_api_failure(mock_get_hist, mock_stream, mock_send):
    from commands.ask import handle_ask

    handle_ask(123, "What is Python?")

    mock_send.assert_called_once()
    assert "could not" in mock_send.call_args[0][1].lower()


def test_estimate_tokens():
    from commands.ask import estimate_tokens

    assert estimate_tokens("") == 1
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 100) == 25


# --- Silent mode tests ---

@patch("commands.ask.call_ollama")
@patch("commands.ask.log_token_usage")
@patch("commands.ask.save_message")
@patch("commands.ask.get_history", return_value=[])
def test_handle_ask_silent_returns_text(mock_get_hist, mock_save, mock_log, mock_call):
    from commands.ask import handle_ask

    mock_call.return_value = {
        "message": {"role": "assistant", "content": "Silent answer"},
        "prompt_eval_count": 10,
        "eval_count": 5,
    }

    result = handle_ask(123, "question", silent=True)

    assert result == "Silent answer"


def test_handle_ask_silent_no_args():
    from commands.ask import handle_ask

    result = handle_ask(123, "", silent=True)

    assert "usage" in result.lower()


def test_call_ollama_with_tools():
    from commands.ask import call_ollama_with_tools

    with patch("commands.ask.requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "message": {"role": "assistant", "content": "ok"},
        }
        mock_post.return_value = mock_resp

        tools = [{"type": "function", "function": {"name": "test"}}]
        call_ollama_with_tools([{"role": "user", "content": "hi"}], tools)

        payload = mock_post.call_args[1]["json"]
        assert "tools" in payload
        assert payload["tools"] == tools
