import os
import uuid
from datetime import datetime

import streamlit as st

import ai_agent
import web_search
from chat_store import DEFAULT_ROOM, ChatStore
from history import HFHistory

REFRESH_SEC = 2
MAX_MESSAGE_LEN = 1000
MAX_NICKNAME = 20

st.set_page_config(page_title="Agent Peoples", page_icon="💬")


def get_setting(name: str, default: str | None = None) -> str | None:
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:  # no secrets.toml present
        pass
    return os.environ.get(name, default)


hf_token = get_setting("HF_TOKEN")
hf_models = list(get_setting("HF_MODELS") or ai_agent.DEFAULT_MODELS)
dataset_repo = get_setting("HF_DATASET_REPO")
tavily_key = get_setting("TAVILY_API_KEY")


@st.cache_resource
def get_store() -> tuple[ChatStore, str | None]:
    """One store per server process, shared by every browser session.

    Returns (store, error) — error is set when saving history could not start.
    """
    if not (hf_token and dataset_repo):
        return ChatStore(), None
    try:
        history = HFHistory(dataset_repo, hf_token)
    except Exception as e:
        return ChatStore(), str(e)
    store = ChatStore(listener=history.append)
    store.restore(history.load())
    return store, None


store, history_error = get_store()

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
if "room" not in st.session_state:
    st.session_state.room = DEFAULT_ROOM

# ---- Sidebar: nickname, rooms, AI status ----
with st.sidebar:
    st.header("💬 Agent Peoples")
    nickname = st.text_input("닉네임", max_chars=MAX_NICKNAME, key="nickname").strip()

    # The form comes before the room selectbox: a widget's session_state key
    # can only be set before that widget is drawn in the current run.
    with st.form("new_room", clear_on_submit=True):
        new_room = st.text_input("새 채팅방 만들기")
        if st.form_submit_button("만들기") and new_room.strip():
            st.session_state.room = store.create_room(new_room)

    st.selectbox("채팅방", store.rooms(), key="room")

    st.divider()
    if hf_token:
        st.success("AI 연결됨")
        hf_model = st.selectbox("AI 모델", hf_models, key="hf_model")
        st.caption("메시지를 `@AI`로 시작하면 선택한 모델이 답합니다. "
                   "실시간 정보가 필요하면 AI가 웹검색을 합니다.")
        st.caption("🔎 검색: " + ("Tavily (실패 시 DuckDuckGo)" if tavily_key else "DuckDuckGo"))
    else:
        st.warning("HF_TOKEN이 설정되지 않아 AI를 사용할 수 없습니다.")

    if history_error:
        st.error(f"대화 기록 저장 실패: {history_error}")
    elif dataset_repo and hf_token:
        st.caption(f"💾 기록 저장: `{dataset_repo}` (1분마다)")
    else:
        st.caption("💾 기록 저장 꺼짐 (HF_DATASET_REPO 미설정)")

room = st.session_state.room
st.subheader(f"# {room}")

if not nickname:
    st.info("왼쪽 사이드바에 닉네임을 입력하면 대화에 참여할 수 있습니다.")
    st.stop()


@st.fragment(run_every=REFRESH_SEC)
def chat_view():
    store.touch(room, st.session_state.session_id, nickname)
    st.caption("접속 중: " + ", ".join(store.online(room)))
    for m in store.messages(room):
        with st.chat_message("assistant" if m.is_ai else "user", avatar="🤖" if m.is_ai else None):
            st.markdown(f"**{m.author}** · {datetime.fromtimestamp(m.ts, ai_agent.TIMEZONE):%m-%d %H:%M:%S}")
            st.markdown(m.text)


chat_view()

if text := st.chat_input("메시지 입력 (@AI 로 AI 호출)", max_chars=MAX_MESSAGE_LEN):
    store.add_message(room, nickname, text)
    if ai_agent.is_ai_mention(text):
        if not hf_token:
            store.add_message(room, ai_agent.AI_NAME, "HF_TOKEN이 설정되지 않아 답할 수 없습니다.", is_ai=True)
        else:
            def search(query: str) -> str:
                return web_search.format_results(web_search.search(query, tavily_key))

            with st.spinner("AI가 답변을 작성 중입니다..."):
                try:
                    reply = ai_agent.ask(hf_token, hf_model, store.messages(room), search)
                except Exception as e:
                    reply = f"AI 호출 실패: {e}"
            author = f"{ai_agent.AI_NAME} · {ai_agent.split_provider(hf_model)[0].split('/')[-1]}"
            store.add_message(room, author, reply or "(빈 응답)", is_ai=True)
    st.rerun()
