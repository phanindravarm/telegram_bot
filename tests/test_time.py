import re
from unittest.mock import patch
from datetime import datetime, timezone


@patch("commands.time.send_message")
def test_handle_time_matches_pattern(mock_send):
    from commands.time import handle_time

    handle_time(123, "")

    mock_send.assert_called_once()
    text = mock_send.call_args[0][1]
    assert re.match(r"Current time: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} IST", text)


@patch("commands.time.send_message")
@patch("commands.time.datetime")
def test_handle_time_frozen(mock_dt, mock_send):
    from commands.time import handle_time

    fixed = datetime(2026, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
    mock_dt.now.return_value = fixed
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

    handle_time(123, "")

    mock_send.assert_called_once_with(123, "Current time: 2026-01-15 12:30:45 IST")
