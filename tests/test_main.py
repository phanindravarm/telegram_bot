from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


def _make_update(message):
    return {"message": message}


def _text_message(chat_id, text):
    return _make_update({"chat": {"id": chat_id}, "text": text})


def _photo_message(chat_id, caption="", file_id="photo_123"):
    return _make_update({
        "chat": {"id": chat_id},
        "photo": [{"file_id": file_id}],
        "caption": caption,
    })


def _document_message(chat_id, caption="", file_id="doc_123", file_name="file.pdf", mime_type="application/pdf"):
    return _make_update({
        "chat": {"id": chat_id},
        "document": {"file_id": file_id, "file_name": file_name, "mime_type": mime_type},
        "caption": caption,
    })


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# --- no message key ---

@pytest.mark.anyio
async def test_webhook_no_message(client):
    resp = await client.post("/webhook", json={"update_id": 1})
    assert resp.status_code == 200


# --- text command routing ---

@pytest.mark.anyio
@patch("main.COMMANDS", {"/help": MagicMock()})
async def test_webhook_known_command(client):
    from main import COMMANDS
    resp = await client.post("/webhook", json=_text_message(123, "/help"))
    assert resp.status_code == 200
    COMMANDS["/help"].assert_called_once_with(123, "")


@pytest.mark.anyio
@patch("main.COMMANDS", {"/help": MagicMock()})
async def test_webhook_command_with_args(client):
    from main import COMMANDS
    resp = await client.post("/webhook", json=_text_message(123, "/help extra args"))
    assert resp.status_code == 200
    COMMANDS["/help"].assert_called_once_with(123, "extra args")


@pytest.mark.anyio
@patch("main.COMMANDS", {"/help": MagicMock()})
async def test_webhook_command_with_botname(client):
    from main import COMMANDS
    resp = await client.post("/webhook", json=_text_message(123, "/help@MyBot"))
    assert resp.status_code == 200
    COMMANDS["/help"].assert_called_once_with(123, "")


@pytest.mark.anyio
@patch("main.send_message")
async def test_webhook_unknown_command(mock_send, client):
    resp = await client.post("/webhook", json=_text_message(123, "/nosuchcmd"))
    assert resp.status_code == 200
    mock_send.assert_called_once_with(123, "Unknown command. Try /help for available commands.")


@pytest.mark.anyio
async def test_webhook_plain_text_no_match_falls_back_to_ask(client):
    mock_ask = MagicMock()
    with patch("agent.run_agent", return_value=None), \
         patch("router.classify_intent", return_value=None), \
         patch.dict("main.COMMANDS", {"/ask": mock_ask}):
        resp = await client.post("/webhook", json=_text_message(123, "hello there"))
    assert resp.status_code == 200
    mock_ask.assert_called_once_with(123, "hello there")


@pytest.mark.anyio
async def test_webhook_plain_text_routed(client):
    mock_weather = MagicMock()
    with patch("agent.run_agent", return_value=None), \
         patch("router.classify_intent", return_value=("/weather", 0.85, "what's the weather in London")), \
         patch.dict("main.COMMANDS", {"/weather": mock_weather}):
        resp = await client.post("/webhook", json=_text_message(123, "what's the weather in London"))
    assert resp.status_code == 200
    mock_weather.assert_called_once_with(123, "what's the weather in London")


@pytest.mark.anyio
async def test_webhook_empty_text(client):
    msg = _make_update({"chat": {"id": 123}, "text": ""})
    resp = await client.post("/webhook", json=msg)
    assert resp.status_code == 200


# --- photo handling ---

@pytest.mark.anyio
async def test_webhook_photo_no_caption(client):
    mock_vision = MagicMock()
    with patch.dict("main.PHOTO_COMMANDS", {"/vision": mock_vision}):
        resp = await client.post("/webhook", json=_photo_message(123))
    assert resp.status_code == 200
    mock_vision.assert_called_once_with(123, "photo_123", "")


@pytest.mark.anyio
async def test_webhook_photo_with_caption(client):
    mock_vision = MagicMock()
    with patch.dict("main.PHOTO_COMMANDS", {"/vision": mock_vision}):
        resp = await client.post("/webhook", json=_photo_message(123, caption="describe this"))
    assert resp.status_code == 200
    mock_vision.assert_called_once_with(123, "photo_123", "describe this")


@pytest.mark.anyio
async def test_webhook_photo_vision_command(client):
    mock_vision = MagicMock()
    with patch.dict("main.PHOTO_COMMANDS", {"/vision": mock_vision}):
        resp = await client.post("/webhook", json=_photo_message(123, caption="/vision what is this"))
    assert resp.status_code == 200
    mock_vision.assert_called_once_with(123, "photo_123", "what is this")


@pytest.mark.anyio
async def test_webhook_photo_vision_command_no_prompt(client):
    mock_vision = MagicMock()
    with patch.dict("main.PHOTO_COMMANDS", {"/vision": mock_vision}):
        resp = await client.post("/webhook", json=_photo_message(123, caption="/vision"))
    assert resp.status_code == 200
    mock_vision.assert_called_once_with(123, "photo_123", "")


# --- document handling ---

@pytest.mark.anyio
async def test_webhook_document_upload(client):
    mock_upload = MagicMock()
    with patch.dict("main.DOCUMENT_COMMANDS", {"/upload": mock_upload, "/summarize": MagicMock()}):
        resp = await client.post("/webhook", json=_document_message(123, caption="/upload"))
    assert resp.status_code == 200
    mock_upload.assert_called_once_with(123, "doc_123", "file.pdf", "application/pdf")


@pytest.mark.anyio
async def test_webhook_document_summarize(client):
    mock_summarize = MagicMock()
    with patch.dict("main.DOCUMENT_COMMANDS", {"/upload": MagicMock(), "/summarize": mock_summarize}):
        resp = await client.post("/webhook", json=_document_message(123, caption="/summarize"))
    assert resp.status_code == 200
    mock_summarize.assert_called_once_with(123, "doc_123", "file.pdf", "application/pdf")


@pytest.mark.anyio
async def test_webhook_document_no_caption(client):
    mock_summarize = MagicMock()
    with patch.dict("main.DOCUMENT_COMMANDS", {"/upload": MagicMock(), "/summarize": mock_summarize}):
        resp = await client.post("/webhook", json=_document_message(123, caption=""))
    assert resp.status_code == 200
    mock_summarize.assert_called_once_with(123, "doc_123", "file.pdf", "application/pdf")


@pytest.mark.anyio
@patch("main.send_message")
async def test_webhook_document_unknown_caption(mock_send, client):
    with patch.dict("main.DOCUMENT_COMMANDS", {"/upload": MagicMock(), "/summarize": MagicMock()}):
        resp = await client.post("/webhook", json=_document_message(123, caption="random text"))
    assert resp.status_code == 200
    mock_send.assert_called_once_with(123, "Send a document with /summarize or /upload caption.")


# --- error handling ---

@pytest.mark.anyio
async def test_webhook_malformed_message(client):
    msg = {"message": {"chat": {}}}
    resp = await client.post("/webhook", json=msg)
    assert resp.status_code == 200


@pytest.mark.anyio
@patch("main.COMMANDS", {"/boom": MagicMock(side_effect=Exception("handler crashed"))})
async def test_webhook_handler_exception(client):
    resp = await client.post("/webhook", json=_text_message(123, "/boom"))
    assert resp.status_code == 200


# --- reschedule_pending_reminders ---

@patch("main.datetime")
def test_reschedule_pending_reminders(mock_dt):
    from main import reschedule_pending_reminders

    mock_dt.now.return_value = datetime_now = MagicMock()
    mock_dt.fromisoformat.return_value = MagicMock()
    mock_dt.fromisoformat.return_value.replace.return_value = MagicMock()

    trigger = mock_dt.fromisoformat.return_value.replace.return_value
    (trigger - datetime_now).total_seconds.return_value = 60.0

    with patch("main.get_pending_reminders", create=True) as mock_get, \
         patch("main.schedule_reminder", create=True) as mock_sched:
        # Patch the lazy imports inside the function
        with patch.dict("sys.modules", {}):
            pass
        import main as m
        with patch("db.get_pending_reminders", return_value=[(1, 123, "test", "2026-03-31T12:00:00")], create=True) as mock_get_db, \
             patch("commands.remind.schedule_reminder") as mock_sched_cmd:
            reschedule_pending_reminders()
            mock_sched_cmd.assert_called_once()


# --- set_webhook ---

@patch("main.requests.post")
def test_set_webhook(mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True}
    mock_post.return_value = mock_resp

    from main import set_webhook
    set_webhook("https://example.ngrok.io")
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "/setWebhook" in call_args[0][0]
    assert call_args[1]["json"]["url"] == "https://example.ngrok.io/webhook"
