# 💬 Agent Peoples

여러 브라우저로 접속한 사람들이 같은 채팅방에서 대화하고, 메시지를 `@AI`로 시작하면 Hugging Face 모델(AI 에이전트 호스트)이 대화에 참여하는 Streamlit 채팅 서비스입니다.

## 기능

- 닉네임 입력 후 채팅 참여
- 여러 채팅방 만들기 / 이동 (기본 방: `lobby`)
- 다른 브라우저의 새 메시지를 2초마다 자동 갱신
- 현재 접속 중인 사람 표시
- `@AI 질문` → 방의 최근 대화 20개를 문맥으로 AI가 답변 (모두에게 보임)
- **웹검색**: 실시간 정보가 필요한 질문이면 AI가 스스로 판단해 웹검색 후 출처와 함께 답변 (Tavily → 실패 시 DuckDuckGo)
- **대화 기록 저장**: Hugging Face 비공개 데이터셋에 1분마다 저장, 앱이 다시 시작되면 자동 복원
- 비밀 값은 코드에 넣지 않고 Streamlit Secrets로 관리

## 구조

| 파일 | 역할 |
|---|---|
| `app.py` | Streamlit 화면 (사이드바, 채팅, 입력) |
| `chat_store.py` | 서버 메모리에 공유되는 채팅방·메시지·접속자 저장소 |
| `ai_agent.py` | `@AI` 감지, Hugging Face `InferenceClient` 호출, `web_search` 도구 호출 처리 |
| `web_search.py` | Tavily / DuckDuckGo 검색 |
| `history.py` | HF 비공개 데이터셋에 기록 저장·불러오기 |
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
2. 토큰 유형 **Fine-grained** 선택 후 아래 권한 체크
   - **Inference** → **Make calls to Inference Providers** (AI 답변)
   - **Repositories** → **Write access to contents/settings of all repos under your personal namespace** (대화 기록 저장용 데이터셋 생성·업로드. 기록 저장을 안 쓰면 생략)
3. 생성된 `hf_...` 값을 복사

## TAVILY_API_KEY 만들기 (선택)

1. https://tavily.com 가입 → 대시보드에서 API 키(`tvly-...`) 복사 (무료: 월 1,000회 검색)
2. 키가 없으면 DuckDuckGo로 검색합니다. DuckDuckGo는 키가 필요 없지만, 서버 IP가 많이 쓰면 가끔 차단되어 검색이 실패할 수 있습니다.

## Streamlit Community Cloud 무료 배포

1. https://share.streamlit.io 에 GitHub 계정으로 로그인
2. **Create app** → **Deploy a public app from GitHub**
3. Repository: `mikedan00/agent_peoples`, Branch: `main`, Main file path: `app.py`
4. **Advanced settings → Secrets**에 아래 내용 붙여넣기 (TOML 형식)

   ```toml
   # 필수: AI 답변 (+ 기록 저장 시 쓰기 권한)
   HF_TOKEN = "hf_여기에_토큰"

   # 선택: 대화 기록을 저장할 비공개 데이터셋 (없으면 자동 생성). 빼면 기록 저장 꺼짐
   HF_DATASET_REPO = "mikedan00/agent_peoples_chats"

   # 선택: Tavily 웹검색 키. 빼면 DuckDuckGo 사용
   TAVILY_API_KEY = "tvly-여기에_키"

   # 선택: 사이드바 "AI 모델" 목록 (첫 번째가 기본값). 빼면 이 기본 목록이 그대로 쓰임
   HF_MODELS = [
     "google/gemma-4-26B-A4B-it:deepinfra",
     "Qwen/Qwen3.6-27B",
     "Qwen/Qwen2.5-7B-Instruct",
   ]
   ```
   - `모델ID:provider` 형식(예: `:deepinfra`)은 그 Inference Provider로 고정해서 호출합니다. 접미사가 없으면 Hugging Face가 사용 가능한 provider를 자동으로 고릅니다.
   - `#`로 시작하는 줄은 설명(주석)이라 그대로 붙여넣어도 됩니다.
   - 따옴표, 대괄호, 쉼표를 그대로 지켜야 합니다. 형식이 틀리면 앱이 Secrets를 읽지 못합니다.
5. **Deploy** → 발급된 `https://...streamlit.app` 주소를 다른 사람과 공유

배포 후 Secrets를 바꾸려면 앱의 **⋮ → Settings → Secrets**에서 수정합니다. 저장하면 앱이 자동으로 다시 시작됩니다.

## AI 모델 선택

각 사용자가 사이드바의 **AI 모델**에서 모델을 고르면, 그 사용자가 `@AI`로 부를 때 해당 모델이 답합니다. AI 답변에는 `AI · 모델이름`이 표시됩니다.

## 웹검색

AI에게 함수 호출(tool calling)로 `web_search` 도구를 제공합니다. 뉴스·가격·날씨처럼 실시간 정보가 필요하면 AI가 검색어를 정해 검색하고, 결과를 바탕으로 출처 URL과 함께 답합니다. 답변 끝에 `🔎 검색: ...`으로 사용한 검색어가 표시됩니다. 함수 호출을 지원하지 않는 모델(또는 provider)은 검색 없이 답합니다.

## 대화 기록 저장 (Hugging Face 데이터셋)

- `HF_DATASET_REPO`에 지정한 **비공개** 데이터셋이 없으면 자동으로 만듭니다.
- 새 채팅방과 메시지를 `data/*.jsonl` 파일에 한 줄씩 쌓고, 1분마다 바뀐 내용을 업로드합니다.
- 앱이 다시 시작되면 저장된 기록을 모두 불러와 채팅방과 최근 메시지(방마다 200개)를 복원합니다.
- 저장된 기록은 `https://huggingface.co/datasets/<HF_DATASET_REPO>`에서 직접 보거나 내려받을 수 있습니다.

## 알아둘 제한

- **마지막 1분 이내의 대화는 잃을 수 있습니다.** 업로드 직전에 앱이 재시작되면 그 사이 메시지는 저장되지 않습니다. 기록 저장을 끄면(`HF_DATASET_REPO` 미설정) 재시작 시 모든 기록이 사라집니다.
- 기록 저장 연결이 실패하면 사이드바에 오류가 표시되고, 앱을 재시작할 때까지 메모리에만 기록됩니다.
- 실시간 푸시가 아니라 2초 간격 갱신 방식입니다.
- 별도 로그인이 없어 닉네임은 누구나 아무 이름으로 쓸 수 있습니다.
- AI 사용량은 Hugging Face 계정의 월 크레딧(Pro는 무료 계정보다 많음)에서 차감되고, 넘으면 요금이 부과될 수 있습니다. 모델이 응답하지 않으면(provider가 없는 모델 등) `HF_MODELS`에서 빼거나, 모델 페이지의 **Inference Providers** 항목에 있는 다른 채팅 모델로 바꾸세요.

## 라이선스

[MIT](LICENSE)
