import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("bot.send_message"):
        from main import app
        client = TestClient(app)
        yield client


def _post(client, data):
    return client.post("/webhook", json=data)


@patch("commands.start.send_message")
def test_webhook_start_command(mock_send, client):
    data = {"message": {"chat": {"id": 123}, "text": "/start"}}
    resp = _post(client, data)

    assert resp.status_code == 200
    assert resp.json() == "OK"
    mock_send.assert_called_once()


@patch("main.send_message")
def test_webhook_unknown_command(mock_send, client):
    data = {"message": {"chat": {"id": 123}, "text": "/foobar"}}
    _post(client, data)

    mock_send.assert_called_once()
    assert "unknown command" in mock_send.call_args[0][1].lower()


def test_webhook_plain_text(client):
    from unittest.mock import MagicMock
    mock_ask = MagicMock()
    with patch("agent.run_agent", return_value=None), \
         patch("router.classify_intent", return_value=None), \
         patch.dict("main.COMMANDS", {"/ask": mock_ask}):
        data = {"message": {"chat": {"id": 123}, "text": "hello there"}}
        _post(client, data)

    mock_ask.assert_called_once_with(123, "hello there")


def test_webhook_no_message_key(client):
    data = {"update_id": 999}
    resp = _post(client, data)

    assert resp.status_code == 200
    assert resp.json() == "OK"


@patch("commands.start.send_message")
def test_webhook_command_with_botname(mock_send, client):
    data = {"message": {"chat": {"id": 123}, "text": "/start@MyBot"}}
    resp = _post(client, data)

    assert resp.status_code == 200
    mock_send.assert_called_once()


def test_webhook_photo_with_vision_caption(client):
    from unittest.mock import MagicMock
    mock_vision = MagicMock()
    with patch.dict("main.PHOTO_COMMANDS", {"/vision": mock_vision}):
        data = {
            "message": {
                "chat": {"id": 123},
                "photo": [
                    {"file_id": "small_id", "width": 90, "height": 90},
                    {"file_id": "large_id", "width": 800, "height": 600},
                ],
                "caption": "/vision What is this?",
            }
        }
        resp = _post(client, data)

    assert resp.status_code == 200
    mock_vision.assert_called_once_with(123, "large_id", "What is this?")


def test_webhook_photo_without_caption(client):
    from unittest.mock import MagicMock
    mock_vision = MagicMock()
    with patch.dict("main.PHOTO_COMMANDS", {"/vision": mock_vision}):
        data = {
            "message": {
                "chat": {"id": 123},
                "photo": [
                    {"file_id": "small_id", "width": 90, "height": 90},
                    {"file_id": "large_id", "width": 800, "height": 600},
                ],
            }
        }
        resp = _post(client, data)

    assert resp.status_code == 200
    mock_vision.assert_called_once_with(123, "large_id", "")