from unittest.mock import patch, ANY

@patch("commands.remind.send_message")
def test_handle_remind_missing_args_empty(mock_send):
    from commands.remind import handle_remind

    handle_remind(123, "")

    mock_send.assert_called_once()
    assert "usage" in mock_send.call_args[0][1].lower()


@patch("commands.remind.send_message")
def test_handle_remind_missing_message(mock_send):
    from commands.remind import handle_remind

    handle_remind(123, "5")

    mock_send.assert_called_once()
    assert "usage" in mock_send.call_args[0][1].lower()


@patch("commands.remind.send_message")
def test_handle_remind_invalid_minutes(mock_send):
    from commands.remind import handle_remind

    handle_remind(123, "abc meeting")

    mock_send.assert_called_once()
    assert "must be a number" in mock_send.call_args[0][1].lower()


@patch("commands.remind.delete_reminder")
@patch("commands.remind.save_reminder")
@patch("commands.remind.send_message")
def test_handle_remind_zero_delay(mock_send, mock_save, mock_delete):
    from commands.remind import handle_remind

    mock_save.return_value = 1

    handle_remind(123, "0 meeting")

    assert mock_send.call_count == 2

    assert "Reminder: meeting" in mock_send.call_args_list[0][0][1]

    assert "Reminder set" in mock_send.call_args_list[1][0][1]

    mock_save.assert_called_once_with(123, "meeting", ANY)

    mock_delete.assert_called_once_with(1)


@patch("commands.remind.schedule_reminder")
@patch("commands.remind.send_message")
@patch("commands.remind.save_reminder")
def test_handle_valid_input(mock_save, mock_send, mock_schedule):
    from commands.remind import handle_remind
    mock_save.return_value = 1

    handle_remind(123, "5 test reminder")

    mock_save.assert_called_once()
    saved_args = mock_save.call_args[0]
    assert saved_args[0] == 123
    assert saved_args[1] == "test reminder"

    mock_send.assert_called_once()
    assert "Reminder set" in mock_send.call_args[0][1]

    mock_schedule.assert_called_once()
    scheduled_args = mock_schedule.call_args[0]
    assert scheduled_args[0] == 1
    assert scheduled_args[1] == 123
    assert scheduled_args[2] == "test reminder"
    assert scheduled_args[3] == 5 * 60


@patch("commands.remind.threading.Timer")
def test_schedule_reminder(mock_timer):
    from commands.remind import schedule_reminder, _fire_reminder

    schedule_reminder(1, 123, "Running", 600)

    mock_timer.assert_called_once()
    args, kwargs = mock_timer.call_args

    assert args[0] == 600
    assert args[1] == _fire_reminder
    assert kwargs["args"] == (1, 123, "Running")

    mock_timer.return_value.start.assert_called_once()


@patch("commands.remind.send_message")
@patch("commands.remind.delete_reminder")
def test_handle_fire_reminder(mock_delete, mock_send):
    from commands.remind import _fire_reminder

    _fire_reminder(1, 123, "Running")

    mock_send.assert_called_once()
    sent_args = mock_send.call_args[0]
    assert sent_args[0] == 123
    assert sent_args[1] == "Reminder: Running"

    mock_delete.assert_called_once_with(1)


@patch("commands.remind.send_message")
def test_handle_remind_negative_time(mock_send):
    from commands.remind import handle_remind

    handle_remind(123, "-1 Run")

    mock_send.assert_called_once()
    assert "Minutes must be positive" in mock_send.call_args[0][1]


@patch("commands.remind.schedule_reminder")
@patch("commands.remind.send_message")
@patch("commands.remind.save_reminder")
def test_handle_remind_fractional_minutes(mock_save, mock_send, mock_schedule):
    from commands.remind import handle_remind
    mock_save.return_value = 1

    handle_remind(123, "0.5 meeting")

    mock_save.assert_called_once()
    saved_args = mock_save.call_args[0]
    assert saved_args[0] == 123
    assert saved_args[1] == "meeting"

    mock_send.assert_called_once()
    assert "Reminder set" in mock_send.call_args[0][1]

    mock_schedule.assert_called_once()
    scheduled_args = mock_schedule.call_args[0]
    assert scheduled_args[0] == 1
    assert scheduled_args[1] == 123
    assert scheduled_args[2] == "meeting"
    assert scheduled_args[3] == 30


@patch("commands.remind._fire_reminder")
def test_schedule_reminder_immediate_fire(mock_fire):
    from commands.remind import schedule_reminder

    schedule_reminder(1, 123, "msg", 0)

    mock_fire.assert_called_once_with(1, 123, "msg")
   