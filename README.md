# 💬 Agent Peoples

여러 브라우저로 접속한 사람들이 같은 채팅방에서 대화하고, 메시지를 `@AI`로 시작하면 Hugging Face 모델(AI 에이전트 호스트)이 대화에 참여하는 Streamlit 채팅 서비스입니다.

## 기능

- 닉네임 입력 후 채팅 참여
- 여러 채팅방 만들기 / 이동 (기본 방: `lobby`)
- 다른 브라우저의 새 메시지를 2초마다 자동 갱신
- 현재 접속 중인 사람 표시
- `@AI 질문` → 방의 최근 대화 20개를 문맥으로 AI가 답변 (모두에게 보임)
- `HF_TOKEN`은 코드에 넣지 않고 Streamlit Secrets로 관리

## 구조

| 파일 | 역할 |
|---|---|
| `app.py` | Streamlit 화면 (사이드바, 채팅, 입력) |
| `chat_store.py` | 서버 메모리에 공유되는 채팅방·메시지·접속자 저장소 |
| `ai_agent.py` | `@AI` 감지, Hugging Face `InferenceClient` 호출 |
| `tests/` | pytest 단위 테스트 |

모든 브라우저는 같은 Streamlit 서버 프로세스에 연결되고, `st.cache_resource`로 만든 하나의 `ChatStore`를 공유합니다.

## 로컬 실행 (VS Code)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # HF_TOKEN 값을 입력
streamlit run app.py
```

VS Code에서는 **실행 및 디버그(Ctrl+Shift+D)** → `Streamlit: app.py`를 선택해 F5로 실행할 수 있습니다 (Python 확장 필요). 브라우저 창을 여러 개(또는 시크릿 창) 열어 `http://localhost:8501`에 접속하면 서로 대화할 수 있습니다.

테스트: `pytest`

## HF_TOKEN 만들기

1. https://huggingface.co/settings/tokens → **Create new token**
2. 토큰 유형 **Fine-grained** → **Make calls to Inference Providers** 권한 체크
3. 생성된 `hf_...` 값을 복사

## Streamlit Community Cloud 무료 배포

1. https://share.streamlit.io 에 GitHub 계정으로 로그인
2. **Create app** → **Deploy a public app from GitHub**
3. Repository: `mikedan00/agent_peoples`, Branch: `main`, Main file path: `app.py`
4. **Advanced settings → Secrets**에 아래 내용 붙여넣기 (TOML 형식)

   **최소 설정** — 토큰만 넣으면 기본 모델 목록이 사용됩니다.
   ```toml
   HF_TOKEN = "hf_여기에_토큰"
   ```

   **모델 목록까지 직접 지정** — 사이드바 "AI 모델"에 이 순서대로 표시되고, 첫 번째가 기본값입니다.
   ```toml
   HF_TOKEN = "hf_여기에_토큰"
   HF_MODELS = [
     "Qwen/Qwen3.6-27B",
     "google/gemma-4-26B-A4B-it:deepinfra",
     "Qwen/Qwen2.5-7B-Instruct",
   ]
   ```
   - `모델ID:provider` 형식(예: `:deepinfra`)은 그 Inference Provider로 고정해서 호출합니다. 접미사가 없으면 Hugging Face가 사용 가능한 provider를 자동으로 고릅니다.
   - 따옴표, 대괄호, 쉼표를 그대로 지켜야 합니다. 형식이 틀리면 앱이 Secrets를 읽지 못합니다.
5. **Deploy** → 발급된 `https://...streamlit.app` 주소를 다른 사람과 공유

배포 후 Secrets를 바꾸려면 앱의 **⋮ → Settings → Secrets**에서 수정합니다. 저장하면 앱이 자동으로 다시 시작됩니다.

## AI 모델 선택

각 사용자가 사이드바의 **AI 모델**에서 모델을 고르면, 그 사용자가 `@AI`로 부를 때 해당 모델이 답합니다. AI 답변에는 `AI · 모델이름`이 표시됩니다.

## 알아둘 제한

- **대화 기록은 서버 메모리에만 있습니다.** 앱이 재시작되거나, 일정 시간 접속이 없어 잠들면 기록이 사라집니다.
- 실시간 푸시가 아니라 2초 간격 갱신 방식입니다.
- 별도 로그인이 없어 닉네임은 누구나 아무 이름으로 쓸 수 있습니다.
- AI 사용량은 Hugging Face 계정의 무료 크레딧에서 차감됩니다. 모델이 응답하지 않으면(provider가 없는 모델 등) `HF_MODELS`에서 빼거나, 모델 페이지의 **Inference Providers** 항목에 있는 다른 채팅 모델로 바꾸세요.

## 라이선스

[MIT](LICENSE)
