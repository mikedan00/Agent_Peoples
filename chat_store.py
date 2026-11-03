"""In-memory chat state shared by every browser connected to one Streamlit server.

Data lives only in server memory: it is lost when the app restarts or sleeps.
"""

import threading
import time
from dataclasses import dataclass

DEFAULT_ROOM = "lobby"
MAX_MESSAGES_PER_ROOM = 200
MAX_ROOM_NAME = 30
PRESENCE_TIMEOUT_SEC = 15


@dataclass(frozen=True)
class Message:
    room: str
    author: str
    text: str
    ts: float
    is_ai: bool = False


class ChatStore:
    def __init__(self, max_messages=MAX_MESSAGES_PER_ROOM, presence_timeout=PRESENCE_TIMEOUT_SEC):
        self._lock = threading.Lock()
        self._max_messages = max_messages
        self._presence_timeout = presence_timeout
        self._rooms: dict[str, list[Message]] = {DEFAULT_ROOM: []}
        # room -> {session_id: (nickname, last_seen)}
        self._presence: dict[str, dict[str, tuple[str, float]]] = {}

    def rooms(self) -> list[str]:
        with self._lock:
            return list(self._rooms)

    def create_room(self, name: str) -> str:
        name = name.strip()[:MAX_ROOM_NAME]
        if not name:
            raise ValueError("방 이름이 비어 있습니다.")
        with self._lock:
            self._rooms.setdefault(name, [])
        return name

    def add_message(self, room: str, author: str, text: str, is_ai: bool = False, now: float | None = None) -> Message:
        msg = Message(room, author, text, now if now is not None else time.time(), is_ai)
        with self._lock:
            msgs = self._rooms.setdefault(room, [])
            msgs.append(msg)
            del msgs[: -self._max_messages]
        return msg

    def messages(self, room: str) -> list[Message]:
        with self._lock:
            return list(self._rooms.get(room, []))

    def touch(self, room: str, session_id: str, nickname: str, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        with self._lock:
            for users in self._presence.values():
                users.pop(session_id, None)  # a session is in one room at a time
            self._presence.setdefault(room, {})[session_id] = (nickname, now)

    def online(self, room: str, now: float | None = None) -> list[str]:
        now = now if now is not None else time.time()
        with self._lock:
            users = self._presence.get(room, {})
            for sid in [s for s, (_, seen) in users.items() if now - seen > self._presence_timeout]:
                del users[sid]
            return sorted({nick for nick, _ in users.values()})
