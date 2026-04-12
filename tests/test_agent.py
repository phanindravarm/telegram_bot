from unittest.mock import patch, MagicMock, ANY


@patch("agent.plan_request", side_effect=lambda t: (t, 0, 0))
@patch("agent.log_token_usage")
@patch("agent.save_message")
@patch("agent.send_message")
@patch("agent.call_ollama_with_tools")
def test_agent_direct_response(mock_call, mock_send, mock_save, mock_log, mock_plan):
    """When LLM returns text without tool calls, send it directly."""
    from agent import run_agent

    mock_call.return_value = {
        "message": {"content": "Hello! How can I help?", "role": "assistant"},
        "prompt_eval_count": 10,
        "eval_count": 5,
    }

    result = run_agent(123, "hi")

    assert result == "Hello! How can I help?"
    mock_send.assert_called_once_with(123, "Hello! How can I help?")
    assert mock_save.call_count == 2  # user + model


@patch("agent.plan_request", side_effect=lambda t: (t, 0, 0))
@patch("agent.log_token_usage")
@patch("agent.save_message")
@patch("agent.send_message")
@patch("agent.execute_tool", return_value="London: +15°C")
@patch("agent.call_ollama_with_tools")
def test_agent_single_tool_call(mock_call, mock_exec, mock_send, mock_save, mock_log, mock_plan):
    """Agent calls one tool, then synthesizes result."""
    from agent import run_agent

    # First call: LLM returns tool call
    mock_call.side_effect = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "weather", "arguments": {"city": "London"}}}
                ],
            },
            "prompt_eval_count": 10,
            "eval_count": 3,
        },
        # Second call: LLM synthesizes
        {
            "message": {"content": "The weather in London is +15°C.", "role": "assistant"},
            "prompt_eval_count": 20,
            "eval_count": 8,
        },
    ]

    result = run_agent(123, "weather in London")

    assert result == "London: +15°C"
    mock_exec.assert_called_once_with("weather", {"city": "London"}, 123, silent=True)


@patch("agent.plan_request", side_effect=lambda t: (t, 0, 0))
@patch("agent.log_token_usage")
@patch("agent.save_message")
@patch("agent.send_message")
@patch("agent.execute_tool")
@patch("agent.call_ollama_with_tools")
def test_agent_multiple_tool_calls(mock_call, mock_exec, mock_send, mock_save, mock_log, mock_plan):
    """Agent calls multiple tools in one step."""
    from agent import run_agent

    mock_exec.side_effect = ["London: +15°C", "Why did the chicken cross the road?\n\nTo get to the other side!"]

    mock_call.side_effect = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "weather", "arguments": {"city": "London"}}},
                    {"function": {"name": "joke", "arguments": {}}},
                ],
            },
            "prompt_eval_count": 10,
            "eval_count": 5,
        },
        {
            "message": {"content": "Here's the weather and a joke!", "role": "assistant"},
            "prompt_eval_count": 30,
            "eval_count": 10,
        },
    ]

    result = run_agent(123, "check weather in London and tell me a joke")

    assert "London: +15°C" in result
    assert "Why did the chicken cross the road?" in result
    assert mock_exec.call_count == 2


@patch("agent.plan_request", side_effect=lambda t: (t, 0, 0))
@patch("agent.log_token_usage")
@patch("agent.save_message")
@patch("agent.send_message")
@patch("agent.call_ollama_with_tools", side_effect=Exception("connection refused"))
def test_agent_ollama_failure_returns_none(mock_call, mock_send, mock_save, mock_log, mock_plan):
    """When Ollama is unreachable, agent returns None for fallback."""
    from agent import run_agent

    result = run_agent(123, "hello")

    assert result is None


@patch("agent.plan_request", side_effect=lambda t: (t, 0, 0))
@patch("agent.log_token_usage")
@patch("agent.save_message")
@patch("agent.send_message")
@patch("agent.execute_tool", return_value="result")
@patch("agent.call_ollama_with_tools")
def test_agent_max_steps(mock_call, mock_exec, mock_send, mock_save, mock_log, mock_plan):
    """Agent stops after max steps and sends partial message."""
    from agent import run_agent, AGENT_MAX_STEPS

    # Always return tool calls, never a final text response
    mock_call.return_value = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "time", "arguments": {}}}
            ],
        },
        "prompt_eval_count": 5,
        "eval_count": 2,
    }

    result = run_agent(123, "infinite loop")

    assert mock_call.call_count == AGENT_MAX_STEPS
    mock_send.assert_called_once()  # sends collected tool results


@patch("agent.plan_request", side_effect=lambda t: (t, 0, 0))
@patch("agent.log_token_usage")
@patch("agent.save_message")
@patch("agent.send_message")
@patch("agent.call_ollama_with_tools")
def test_agent_saves_only_user_and_final(mock_call, mock_send, mock_save, mock_log, mock_plan):
    """Only user message and final answer are saved to history."""
    from agent import run_agent

    mock_call.return_value = {
        "message": {"content": "Final answer", "role": "assistant"},
        "prompt_eval_count": 10,
        "eval_count": 5,
    }

    run_agent(123, "question")

    assert mock_save.call_count == 2
    # First save: user message
    assert mock_save.call_args_list[0][0][1] == "user"
    assert mock_save.call_args_list[0][0][2] == "question"
    # Second save: model response
    assert mock_save.call_args_list[1][0][1] == "model"
    assert mock_save.call_args_list[1][0][2] == "Final answer"


# --- plan_request tests ---


@patch("agent.call_ollama_with_tools")
def test_plan_request_returns_plan_text(mock_call):
    from agent import plan_request

    mock_call.return_value = {
        "message": {"content": "1. Call joke().\n2. Call remind(minutes=2, text=<joke>).", "role": "assistant"},
        "prompt_eval_count": 50,
        "eval_count": 20,
    }

    plan, p_tok, c_tok = plan_request("tell me a joke in 2 minutes")
    assert "1." in plan and "remind" in plan
    assert p_tok == 50
    assert c_tok == 20


@patch("agent.call_ollama_with_tools", side_effect=Exception("ollama down"))
def test_plan_request_falls_back_to_raw_text(mock_call):
    from agent import plan_request

    plan, p_tok, c_tok = plan_request("hello")
    assert plan == "hello"
    assert p_tok == 0 and c_tok == 0


@patch("agent.call_ollama_with_tools")
def test_plan_request_empty_plan_falls_back(mock_call):
    from agent import plan_request

    mock_call.return_value = {
        "message": {"content": "   ", "role": "assistant"},
        "prompt_eval_count": 5,
        "eval_count": 0,
    }

    plan, _, _ = plan_request("hi")
    assert plan == "hi"


@patch("agent.plan_request", return_value=("1. Call joke().\n2. Call ask(question='what is an agent').", 10, 5))
@patch("agent.log_token_usage")
@patch("agent.save_message")
@patch("agent.send_message")
@patch("agent.execute_tool")
@patch("agent.call_ollama_with_tools")
def test_run_agent_uses_plan_as_user_message(mock_call, mock_exec, mock_send, mock_save, mock_log, mock_plan):
    """The plan text — not the raw user input — is what the executor LLM sees."""
    from agent import run_agent

    mock_exec.side_effect = ["a joke", "an agent is..."]
    mock_call.side_effect = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "joke", "arguments": {}}},
                    {"function": {"name": "ask", "arguments": {"question": "what is an agent"}}},
                ],
            },
            "prompt_eval_count": 20,
            "eval_count": 5,
        },
        {
            "message": {"content": "Here you go!", "role": "assistant"},
            "prompt_eval_count": 30,
            "eval_count": 10,
        },
    ]

    run_agent(123, "tell me a joke and what is an agent")

    # Verify the executor was called with the plan as the user message, not the raw input.
    first_call_messages = mock_call.call_args_list[0][0][0]
    user_msg = next(m for m in first_call_messages if m["role"] == "user")
    assert "1." in user_msg["content"]
    assert "ask" in user_msg["content"]
    assert mock_exec.call_count == 2
    # History stores the ORIGINAL user input, not the plan.
    assert mock_save.call_args_list[0][0][2] == "tell me a joke and what is an agent"


def test_substitute_step_refs():
    """Placeholder references like '<the joke from step 1>' are replaced."""
    from agent import _substitute_step_refs

    step_results = {1: "Why did the chicken cross the road?\n\nTo get to the other side!"}

    # Should substitute the placeholder with the actual joke
    args = {"text": "<the joke from step 1>", "minutes": 2}
    result, consumed = _substitute_step_refs(args, step_results)
    assert result["text"] == "Why did the chicken cross the road?\n\nTo get to the other side!"
    assert result["minutes"] == 2  # non-string args untouched
    assert 1 in consumed

    # No step results — args unchanged
    args2 = {"text": "<result from step 1>"}
    result2, consumed2 = _substitute_step_refs(args2, {})
    assert result2 == args2
    assert consumed2 == set()

    # Multiple step refs
    step_results[2] = "sunny"
    args3 = {"msg": "<step 1> and <step 2>"}
    result3, consumed3 = _substitute_step_refs(args3, step_results)
    assert "chicken" in result3["msg"]
    assert "sunny" in result3["msg"]
    assert consumed3 == {1, 2}


@patch("agent.plan_request", side_effect=lambda t: (
    "1. Call joke().\n2. Call remind(minutes=2, text=<the joke from step 1>).", 10, 5
))
@patch("agent.log_token_usage")
@patch("agent.save_message")
@patch("agent.send_message")
@patch("agent.execute_tool")
@patch("agent.call_ollama_with_tools")
def test_run_agent_substitutes_step_refs(mock_call, mock_exec, mock_send, mock_save, mock_log, mock_plan):
    """Step references in tool args are substituted with actual results."""
    from agent import run_agent

    mock_exec.side_effect = [
        "Why did the bagel fly?\n\nA plain bagel.",  # joke result
        "Reminder set for 2.0 minute(s).",            # remind result
    ]
    mock_call.side_effect = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "joke", "arguments": {}}},
                ],
            },
            "prompt_eval_count": 10,
            "eval_count": 5,
        },
        {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "remind", "arguments": {"minutes": 2, "text": "<the joke from step 1>"}}},
                ],
            },
            "prompt_eval_count": 15,
            "eval_count": 5,
        },
        {
            "message": {"content": "Done!", "role": "assistant"},
            "prompt_eval_count": 20,
            "eval_count": 5,
        },
    ]

    run_agent(123, "remind me of a joke in 2 minutes")

    # The remind tool should have received the ACTUAL joke, not the placeholder.
    remind_call = mock_exec.call_args_list[1]
    assert remind_call[0][0] == "remind"  # tool_name
    assert "bagel" in remind_call[0][1]["text"]  # tool_args["text"] has the joke
