from unittest.mock import patch, MagicMock


@patch("commands.summarize.send_message")
def test_handle_summarize_no_args(mock_send):
    from commands.summarize import handle_summarize

    handle_summarize(123, "")

    mock_send.assert_called_once()
    assert "usage" in mock_send.call_args[0][1].lower()


@patch("commands.summarize.send_message")
@patch("commands.summarize.requests")
def test_handle_summarize_success(mock_requests, mock_send):
    from commands.summarize import handle_summarize

    # Mock fetch_page_text via requests.Session().get
    mock_session = MagicMock()
    mock_get_resp = MagicMock()
    mock_get_resp.text = "<html><body><p>This is a long article about Python programming. " + "x" * 100 + "</p></body></html>"
    mock_get_resp.raise_for_status = MagicMock()
    mock_session.get.return_value = mock_get_resp
    mock_requests.Session.return_value = mock_session

    # Mock Ollama API response
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {
        "message": {"role": "assistant", "content": "Summary of the article."}
    }
    mock_post_resp.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_post_resp

    handle_summarize(123, "https://example.com/article")

    mock_send.assert_called_once_with(123, "Summary of the article.")


@patch("commands.summarize.send_message")
@patch("commands.summarize.requests")
def test_handle_summarize_prepends_https(mock_requests, mock_send):
    from commands.summarize import handle_summarize

    mock_session = MagicMock()
    mock_get_resp = MagicMock()
    mock_get_resp.text = "<html><body>" + "Some content. " * 20 + "</body></html>"
    mock_get_resp.raise_for_status = MagicMock()
    mock_session.get.return_value = mock_get_resp
    mock_requests.Session.return_value = mock_session

    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {
        "message": {"role": "assistant", "content": "A summary."}
    }
    mock_post_resp.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_post_resp

    handle_summarize(123, "example.com")

    # Verify https:// was prepended
    call_url = mock_session.get.call_args[0][0]
    assert call_url == "https://example.com"


@patch("commands.summarize.send_message")
@patch("commands.summarize.fetch_page_text", side_effect=Exception("network error"))
def test_handle_summarize_fetch_failure(mock_fetch, mock_send):
    from commands.summarize import handle_summarize

    handle_summarize(123, "https://example.com")

    mock_send.assert_called_once()
    assert "could not fetch" in mock_send.call_args[0][1].lower()


@patch("commands.summarize.send_message")
@patch("commands.summarize.fetch_page_text", return_value="short")
def test_handle_summarize_not_enough_text(mock_fetch, mock_send):
    from commands.summarize import handle_summarize

    handle_summarize(123, "https://example.com")

    mock_send.assert_called_once()
    assert "not extract enough" in mock_send.call_args[0][1].lower()


@patch("commands.summarize.send_message")
@patch("commands.summarize.fetch_page_text", return_value="x" * 100)
@patch("commands.summarize.requests")
def test_handle_summarize_api_failure(mock_requests, mock_fetch, mock_send):
    from commands.summarize import handle_summarize

    mock_requests.post.side_effect = Exception("API error")

    handle_summarize(123, "https://example.com")

    mock_send.assert_called_once()
    assert "could not generate" in mock_send.call_args[0][1].lower()


def test_fetch_page_text_strips_html():
    from commands.summarize import fetch_page_text

    html = "<html><head><script>var x=1;</script><style>.a{}</style></head><body><p>Hello world</p></body></html>"

    with patch("commands.summarize.requests") as mock_requests:
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        result = fetch_page_text("https://example.com")

    assert "Hello world" in result
    assert "<script>" not in result
    assert "<style>" not in result
    assert "<p>" not in result


def test_fetch_page_text_truncates_long_content():
    from commands.summarize import fetch_page_text

    html = "<body>" + "a" * 20000 + "</body>"

    with patch("commands.summarize.requests") as mock_requests:
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        result = fetch_page_text("https://example.com")

    assert len(result) <= 10000


# --- Document handler tests ---

@patch("commands.summarize.send_message")
@patch("commands.summarize.requests")
@patch("commands.summarize.get_file_url", return_value="https://api.telegram.org/file/bot123/doc.txt")
def test_handle_summarize_document_success(mock_get_file_url, mock_requests, mock_send):
    from commands.summarize import handle_summarize_document

    # Mock file download
    mock_download_resp = MagicMock()
    mock_download_resp.content = ("This is a sample text document with enough content to summarize. " * 5).encode()
    mock_download_resp.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_download_resp

    # Mock Ollama API response
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {
        "message": {"role": "assistant", "content": "Document summary."}
    }
    mock_post_resp.raise_for_status = MagicMock()
    mock_requests.post.return_value = mock_post_resp

    handle_summarize_document(123, "file_id_123", "notes.txt", "text/plain")

    mock_send.assert_called_once_with(123, "Document summary.")


@patch("commands.summarize.send_message")
@patch("commands.summarize.get_file_url", side_effect=Exception("download failed"))
def test_handle_summarize_document_download_failure(mock_get_file_url, mock_send):
    from commands.summarize import handle_summarize_document

    handle_summarize_document(123, "file_id_123", "notes.pdf", "application/pdf")

    mock_send.assert_called_once()
    assert "could not download" in mock_send.call_args[0][1].lower()


@patch("commands.summarize.send_message")
@patch("commands.summarize.requests")
@patch("commands.summarize.get_file_url", return_value="https://example.com/file")
def test_handle_summarize_document_unsupported_type(mock_get_file_url, mock_requests, mock_send):
    from commands.summarize import handle_summarize_document

    mock_download_resp = MagicMock()
    mock_download_resp.content = b"some bytes"
    mock_download_resp.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_download_resp

    handle_summarize_document(123, "file_id_123", "image.png", "image/png")

    mock_send.assert_called_once()
    assert "unsupported" in mock_send.call_args[0][1].lower()


@patch("commands.summarize.send_message")
@patch("commands.summarize.requests")
@patch("commands.summarize.get_file_url", return_value="https://example.com/file")
def test_handle_summarize_document_not_enough_text(mock_get_file_url, mock_requests, mock_send):
    from commands.summarize import handle_summarize_document

    mock_download_resp = MagicMock()
    mock_download_resp.content = b"short"
    mock_download_resp.raise_for_status = MagicMock()
    mock_requests.get.return_value = mock_download_resp

    handle_summarize_document(123, "file_id_123", "notes.txt", "text/plain")

    mock_send.assert_called_once()
    assert "not extract enough" in mock_send.call_args[0][1].lower()
