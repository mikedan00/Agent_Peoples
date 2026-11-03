"""Hugging Face AI agent that answers chat messages starting with @AI.

The agent offers the model a web_search tool; the model decides when it
needs current information. Models whose provider rejects tools still
answer, just without search.
"""

import json
from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

from huggingface_hub import InferenceClient

from chat_store import Message

# Models users can pick in the sidebar. "model:provider" pins an Inference
# Provider; without a suffix Hugging Face picks one automatically.
# Override the whole list with HF_MODELS in Streamlit Secrets.
DEFAULT_MODELS = [
    "google/gemma-4-26B-A4B-it:deepinfra",
    "Qwen/Qwen3.6-27B",
    "Qwen/Qwen2.5-7B-Instruct",
]
AI_NAME = "AI"
MENTION = "@ai"
HISTORY_LIMIT = 20
MAX_TOOL_ROUNDS = 3
TIMEZONE = ZoneInfo("Asia/Seoul")
SYSTEM_PROMPT = (
    "You are the AI host of a group chat room. Several people talk here at once; "
    "each user message is prefixed with the speaker's nickname. "
    "Answer the person who called you, briefly and helpfully, in the language they used. "
    "Current date and time: {now} (Asia/Seoul). "
    "If the question needs current or real-time information (news, prices, weather, "
    "recent events, anything after your training data), call the web_search tool and "
    "cite the URLs you used."
)
TOOLS = [{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current or real-time information.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
}]


def is_ai_mention(text: str) -> bool:
    return text.strip().lower().startswith(MENTION)


def build_messages(history: list[Message], limit: int = HISTORY_LIMIT, now: datetime | None = None) -> list[dict]:
    """Turn recent room history into chat-completion messages."""
    now = now or datetime.now(TIMEZONE)
    out = [{"role": "system", "content": SYSTEM_PROMPT.format(now=f"{now:%Y-%m-%d %H:%M}")}]
    for m in history[-limit:]:
        if m.is_ai:
            out.append({"role": "assistant", "content": m.text})
        else:
            out.append({"role": "user", "content": f"{m.author}: {m.text}"})
    return out


def split_provider(model: str) -> tuple[str, str | None]:
    """'org/model:provider' -> ('org/model', 'provider'); no suffix -> provider None (auto)."""
    name, _, provider = model.partition(":")
    return name, provider or None


def ask(token: str, model: str, history: list[Message], search: Callable[[str], str],
        max_tokens: int = 1024, client=None) -> str:
    """Answer the latest message. `search(query)` returns formatted search results."""
    if client is None:
        name, provider = split_provider(model)
        client = InferenceClient(model=name, provider=provider, token=token, timeout=90)
    messages = build_messages(history)

    try:
        resp = client.chat_completion(messages, tools=TOOLS, tool_choice="auto", max_tokens=max_tokens)
    except Exception:
        # The provider may not support tools: answer without search.
        resp = client.chat_completion(messages, max_tokens=max_tokens)
        return (resp.choices[0].message.content or "").strip()

    queries = []
    for _ in range(MAX_TOOL_ROUNDS):
        msg = resp.choices[0].message
        if not msg.tool_calls:
            break
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": _as_json(c.function.arguments)}}
                           for c in msg.tool_calls],
        })
        for c in msg.tool_calls:
            query = _parse_args(c.function.arguments).get("query", "")
            queries.append(query)
            try:
                result = search(query)
            except Exception as e:
                result = f"Search failed: {e}"
            messages.append({"role": "tool", "tool_call_id": c.id, "content": result})
        resp = client.chat_completion(messages, tools=TOOLS, tool_choice="auto", max_tokens=max_tokens)

    answer = (resp.choices[0].message.content or "").strip()
    if queries:
        answer += "\n\n🔎 검색: " + ", ".join(f"`{q}`" for q in queries)
    return answer


def _parse_args(arguments) -> dict:
    if isinstance(arguments, dict):
        return arguments
    try:
        return json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return {}


def _as_json(arguments) -> str:
    return arguments if isinstance(arguments, str) else json.dumps(arguments, ensure_ascii=False)
