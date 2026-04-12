from unittest.mock import patch, MagicMock


@patch("commands.vision.send_message")
@patch("commands.vision.client")
@patch("commands.vision.requests")
@patch("commands.vision.get_file_url", return_value="https://example.com/photo.jpg")
@patch("commands.vision.HF_TOKEN", "fake-key")
def test_handle_vision_success(
    mock_get_url,
    mock_requests,
    mock_client,
    mock_send
):
    from commands.vision import handle_vision

    mock_download = MagicMock()
    mock_download.content = b"fake-image-bytes"
    mock_download.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_download

    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="A cute cat."))
    ]
    mock_client.chat.completions.create.return_value = mock_completion

    handle_vision(123, "file_abc")

    mock_send.assert_called_once_with(123, "A cute cat.")

from unittest.mock import patch, MagicMock

@patch("commands.vision.send_message")
@patch("commands.vision.client")
@patch("commands.vision.requests")
@patch("commands.vision.get_file_url", return_value="https://example.com/photo.jpg")
@patch("commands.vision.HF_TOKEN", "fake-key")
def test_handle_vision_with_custom_prompt(
    mock_get_url,
    mock_requests,
    mock_client,
    mock_send
):
    from commands.vision import handle_vision

    mock_download = MagicMock()
    mock_download.content = b"fake-image-bytes"
    mock_download.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_download

    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="It's a golden retriever."))
    ]
    mock_client.chat.completions.create.return_value = mock_completion

    handle_vision(123, "file_abc", "What breed is this dog?")

    call_args = mock_client.chat.completions.create.call_args[1]
    messages = call_args["messages"]

    assert messages[0]["content"][0]["text"] == "What breed is this dog?"


@patch("commands.vision.send_message")
@patch("commands.vision.client")
@patch("commands.vision.requests")
@patch("commands.vision.get_file_url", return_value="https://example.com/photo.jpg")
@patch("commands.vision.HF_TOKEN", "fake-key")
def test_handle_vision_default_prompt(mock_get_url, mock_requests,  mock_client, mock_send):
    from commands.vision import handle_vision, DEFAULT_PROMPT

    mock_download = MagicMock()
    mock_download.content = b"fake-image-bytes"
    mock_download.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_download
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="A landscape."))
    ]
    mock_client.chat.completions.create.return_value = mock_completion

    handle_vision(123, "file_abc", "")

    call_args = mock_client.chat.completions.create.call_args[1]
    messages = call_args["messages"]

    assert messages[0]["content"][0]["text"] == DEFAULT_PROMPT

    mock_send.assert_called_once_with(123, "A landscape.")


@patch("commands.vision.send_message")
def test_handle_vision_missing_api_key(mock_send):
    from commands.vision import handle_vision

    with patch("commands.vision.HF_TOKEN", ""):
        handle_vision(123, "file_abc")

    mock_send.assert_called_once()
    assert "not configured" in mock_send.call_args[0][1].lower()


@patch("commands.vision.send_message")
@patch("commands.vision.get_file_url", side_effect=Exception("network error"))
@patch("commands.vision.HF_TOKEN", "fake-key")
def test_handle_vision_download_failure(mock_get_url, mock_send):
    from commands.vision import handle_vision

    handle_vision(123, "file_abc")

    mock_send.assert_called_once()
    assert "could not download" in mock_send.call_args[0][1].lower()


@patch("commands.vision.send_message")
@patch("commands.vision.requests")
@patch("commands.vision.get_file_url", return_value="https://example.com/photo.jpg")
@patch("commands.vision.HF_TOKEN", "fake-key")
def test_handle_vision_api_failure(mock_get_url, mock_requests, mock_send):
    from commands.vision import handle_vision

    mock_download = MagicMock()
    mock_download.content = b"fake-image-bytes"
    mock_download.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_download

    mock_requests.post.side_effect = Exception("API error")

    handle_vision(123, "file_abc")

    mock_send.assert_called_once()
    assert "could not analyze" in mock_send.call_args[0][1].lower()
