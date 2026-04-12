from unittest.mock import patch


@patch("commands.clear.send_message")
@patch("commands.clear.clear_history")
def test_handle_clear(mock_clear, mock_send):
    from commands.clear import handle_clear

    handle_clear(456, "")

    mock_clear.assert_called_once_with(456)
    mock_send.assert_called_once()
    assert "cleared" in mock_send.call_args[0][1].lower()
