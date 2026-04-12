"""AI Agent with ReAct-style planning and multi-step tool execution."""

import json
import logging
import re

from bot import send_message
from db import save_message, log_token_usage
from commands.ask import build_messages, estimate_tokens, call_ollama_with_tools, call_ollama
from commands.ask_config import TOOL_USE_MODEL, AGENT_MAX_STEPS
from commands.stream import stream_to_telegram
from tools import get_tool_definitions, execute_tool

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = (
    "You are a task planner for a Telegram bot. Rewrite the user's request as a "
    "numbered list of explicit steps that the bot's agent must execute. Each step "
    "should describe exactly one tool action. If a step depends on the result of "
    "an earlier step, say so explicitly.\n\n"
    "Available tools:\n"
    "- weather(city): current weather for a city\n"
    "- joke(): a random joke\n"
    "- time(): current time in IST\n"
    "- worldtime(): time across timezones\n"
    "- remind(minutes, text): schedule `text` to be sent N minutes from now\n"
    "- summarize(url): summarize a web page\n"
    "- query(question): search the user's indexed knowledge base\n"
    "- ask(question): general AI question (use for definitions, explanations, factual Q&A)\n\n"
    "RULES:\n"
    "1. If the user's request contains a future time qualifier ('in N minutes', 'in N "
    "hours', 'at <time>', 'tomorrow', 'later'), the action is NOT immediate — it must "
    "be wrapped in remind. First fetch the content, then schedule it via remind.\n"
    "2. If the user has multiple distinct requests (joined by 'and', 'also', 'then', "
    "or as separate sentences), list every one as its own step(s). Never drop a request.\n"
    "3. Output ONLY the numbered list, no preamble, no explanation, no closing text.\n"
    "4. If the request is a simple greeting or direct chat with no tool needed, output "
    "the original user message verbatim with no numbering.\n\n"
    "EXAMPLES:\n"
    "User: tell me a joke in 2 minutes\n"
    "Plan:\n"
    "1. Call joke() to get a joke.\n"
    "2. Call remind(minutes=2, text=<the joke from step 1>) to schedule it.\n\n"
    "User: tell me a joke and what is an agent\n"
    "Plan:\n"
    "1. Call joke() to get a joke.\n"
    "2. Call ask(question='what is an agent') to answer the second question.\n\n"
    "User: weather in Paris and remind me to drink water in 10 minutes\n"
    "Plan:\n"
    "1. Call weather(city='Paris').\n"
    "2. Call remind(minutes=10, text='drink water').\n\n"
    "User: hi how are you\n"
    "Plan:\n"
    "hi how are you\n"
)


def plan_request(user_text):
    """Use the LLM to rewrite a user request as a numbered action plan.

    Returns the plan text (or the original user_text if planning fails).
    """
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": f"User: {user_text}\nPlan:\n"},
    ]
    try:
        data = call_ollama_with_tools(messages, tools=[], model=TOOL_USE_MODEL)
        plan = data.get("message", {}).get("content", "").strip()
        if not plan:
            return user_text, 0, 0
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        return plan, prompt_tokens, completion_tokens
    except Exception as e:
        logger.warning("Planner call failed, using raw user text: %s", e)
        return user_text, 0, 0

def _substitute_step_refs(tool_args, step_results):
    """Replace placeholder references like '<the joke from step 1>' in tool
    arguments with the actual result from that step.

    Also auto-fills empty string arguments with the most recent step result,
    since small LLMs often omit the dependent value entirely.

    Returns (substituted_args, consumed_step_nums).
    """
    if not step_results:
        return tool_args, set()

    pattern = re.compile(r"<[^>]*step\s+(\d+)[^>]*>", re.IGNORECASE)
    last_step_num = max(step_results)
    last_result = step_results[last_step_num]
    consumed = set()

    def _replace(value):
        if not isinstance(value, str):
            return value

        # Substitute explicit <step N> references.
        def _sub(m):
            step_num = int(m.group(1))
            consumed.add(step_num)
            return step_results.get(step_num, m.group(0))

        result = pattern.sub(_sub, value)

        # If the value is still empty or is a bare placeholder the LLM
        # didn't format with "step N", fill in the most recent result.
        if not result.strip() or result.strip().startswith("<"):
            consumed.add(last_step_num)
            return last_result

        return result

    new_args = {k: _replace(v) for k, v in tool_args.items()}
    return new_args, consumed


AGENT_SYSTEM_PROMPT = (
    "You are a helpful Telegram bot assistant with access to tools. "
    "The user message you receive may be a numbered action plan. Execute every "
    "numbered step in order by calling the appropriate tool. Do not stop "
    "until every step has been performed.\n\n"
    "If a step refers to the result of an earlier step (e.g. '<the joke from step 1>'), "
    "use the actual value returned by the previous tool call as the argument.\n\n"
    "IMPORTANT: Your final text response is sent directly to the user on Telegram. "
    "You MUST include the actual content returned by the tools — do NOT summarize, "
    "paraphrase, or comment on results instead of showing them. "
    "NEVER mention steps, plans, numbering, tool names, or internal reasoning. "
    "For example, if a joke tool returned a joke, your entire response should be "
    "the joke itself, nothing more. If multiple tools returned results, combine "
    "all their outputs naturally."
)


def run_agent(chat_id, user_text):
    """Run the agent loop: plan, execute tools, synthesize response.

    Sends the final answer to Telegram (streamed). Saves only user input
    and final answer to conversation history.
    """
    # Pre-step: rewrite the user request as a numbered action plan.
    plan, plan_prompt_tokens, plan_completion_tokens = plan_request(user_text)
    logger.info("Agent plan for %r: %s", user_text, plan)

    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": plan},
    ]
    tools = get_tool_definitions()
    total_prompt_tokens = plan_prompt_tokens
    total_completion_tokens = plan_completion_tokens

    tool_results = []      # (step_num, result) pairs for the final response
    step_results = {}      # Map step number (1-based) to tool result for substitution
    consumed_steps = set() # Steps whose results were fed into a later tool

    for step in range(AGENT_MAX_STEPS):
        try:
            data = call_ollama_with_tools(messages, tools, model=TOOL_USE_MODEL)
        except Exception as e:
            logger.error("Agent Ollama call failed: %s", e)
            return None  # Signal caller to fall back

        total_prompt_tokens += data.get("prompt_eval_count", 0)
        total_completion_tokens += data.get("eval_count", 0)

        response_message = data.get("message", {})
        tool_calls = response_message.get("tool_calls")

        if not tool_calls:
            # No tool call — LLM is done.
            # Filter out intermediate results that were consumed by later tools.
            visible = [r for sn, r in tool_results if sn not in consumed_steps]
            if visible:
                final_text = "\n\n".join(visible)
            else:
                # No tools were ever called — pure conversational reply.
                final_text = response_message.get("content", "")

            if final_text:
                send_message(chat_id, final_text)
            else:
                send_message(chat_id, "I couldn't generate a response. Try again.")
                final_text = ""

            # Save to conversation history
            user_tokens = estimate_tokens(user_text)
            model_tokens = estimate_tokens(final_text)
            save_message(chat_id, "user", user_text, user_tokens)
            save_message(chat_id, "model", final_text, model_tokens)
            log_token_usage(chat_id, total_prompt_tokens, total_completion_tokens)
            return final_text

        # Execute tool calls
        messages.append(response_message)

        for tool_call in tool_calls:
            func = tool_call.get("function", {})
            tool_name = func.get("name", "")
            tool_args = func.get("arguments", {})

            # Substitute placeholders like "<the joke from step 1>" with
            # the actual result from that step.
            tool_args, refs_consumed = _substitute_step_refs(tool_args, step_results)
            consumed_steps.update(refs_consumed)

            # Auto-fill missing 'text' for remind if we have prior results.
            if tool_name == "remind" and not tool_args.get("text") and step_results:
                last_num = max(step_results)
                tool_args["text"] = step_results[last_num]
                consumed_steps.add(last_num)

            logger.info("Agent calling tool: %s(%s)", tool_name, tool_args)

            try:
                result = execute_tool(tool_name, tool_args, chat_id, silent=True)
            except Exception as e:
                result = f"Error executing {tool_name}: {e}"

            # Track result by 1-based tool call number.
            current_step = len(step_results) + 1
            step_results[current_step] = result or ""

            messages.append({
                "role": "tool",
                "content": result or "Done (no output).",
            })

            # Collect non-trivial results for the final response.
            if result and result != "Done (no output).":
                tool_results.append((current_step, result))

    # Max steps exceeded — send whatever tool results we collected.
    visible = [r for sn, r in tool_results if sn not in consumed_steps]
    if visible:
        final_text = "\n\n".join(visible)
        send_message(chat_id, final_text)
    else:
        final_text = ""
        send_message(
            chat_id,
            "I reached the maximum number of steps. Here's what I found so far based on the tools I used.",
        )

    # Save conversation
    user_tokens = estimate_tokens(user_text)
    save_message(chat_id, "user", user_text, user_tokens)
    save_message(chat_id, "model", final_text or "(agent reached max steps)", 5)
    log_token_usage(chat_id, total_prompt_tokens, total_completion_tokens)
    return final_text or None
