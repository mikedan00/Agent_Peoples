"""Hugging Face AI agent that answers chat messages starting with @AI."""

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


def split_provider(model: str) -> tuple[str, str | None]:
    """'org/model:provider' -> ('org/model', 'provider'); no suffix -> provider None (auto)."""
    name, _, provider = model.partition(":")
    return name, provider or None


def ask(token: str, model: str, history: list[Message], max_tokens: int = 512) -> str:
    name, provider = split_provider(model)
    client = InferenceClient(model=name, provider=provider, token=token, timeout=60)
    resp = client.chat_completion(build_messages(history), max_tokens=max_tokens)
    return (resp.choices[0].message.content or "").strip()
