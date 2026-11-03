"""Hugging Face AI agent that answers chat messages starting with @AI."""

from huggingface_hub import InferenceClient

from chat_store import Message

DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
AI_NAME = "AI"
MENTION = "@ai"
HISTORY_LIMIT = 20
SYSTEM_PROMPT = (
    "You are the AI host of a group chat room. Several people talk here at once; "
    "each user message is prefixed with the speaker's nickname. "
    "Answer the person who called you, briefly and helpfully, in the language they used."
)


def is_ai_mention(text: str) -> bool:
    return text.strip().lower().startswith(MENTION)


def build_messages(history: list[Message], limit: int = HISTORY_LIMIT) -> list[dict]:
    """Turn recent room history into chat-completion messages."""
    out = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-limit:]:
        if m.is_ai:
            out.append({"role": "assistant", "content": m.text})
        else:
            out.append({"role": "user", "content": f"{m.author}: {m.text}"})
    return out


def ask(token: str, model: str, history: list[Message], max_tokens: int = 512) -> str:
    client = InferenceClient(model=model, token=token, timeout=60)
    resp = client.chat_completion(build_messages(history), max_tokens=max_tokens)
    return (resp.choices[0].message.content or "").strip()
