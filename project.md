# CookMate Agent — 프로젝트 가이드

보유 식재료(pantries)를 입력받아 레시피를 추천·생성하는 **FastAPI + LangGraph 기반 AI Agent 서버**입니다.
상위 서비스인 **Spring Boot 백엔드**가 이 서버를 HTTP로 호출하고, 이 서버는 외부 레시피 소스(식약처 API, Spoonacular, Tavily 웹 검색)에서 원천 데이터를 모은 뒤 LLM(OpenAI)으로 Spring Boot 엔티티 형식에 맞는 레시피를 만들어 돌려줍니다.

```
Spring Boot ──POST /api/recipe/generate──▶ FastAPI (routers/recipe.py)
                                              │
                                              ▼
                                LangGraph Agent (agent/)
                    ┌─────────────────────────┼──────────────────────────┐
                    ▼                         ▼                          ▼
           식약처 COOKRCP01 API         Tavily 웹 검색           Spoonacular API
                    └──────────── raw_data ───┴──────────────────────────┘
                                              ▼
                              OpenAI gpt-4o-mini (structured output)
                                              ▼
                              RecipeResponse (JSON) ──▶ Spring Boot
```

---

## 1. 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 언어 | Python 3.10+ (`list[str]` 등 내장 제네릭 문법 사용) |
| 웹 프레임워크 / 서버 | FastAPI ≥ 0.115, Uvicorn ≥ 0.30 |
| 데이터 검증 | Pydantic v2 (≥ 2.8) |
| Agent 파이프라인 | LangGraph ≥ 0.2, LangChain ≥ 0.3 |
| LLM | `langchain-openai` — `ChatOpenAI(model="gpt-4o-mini")` |
| 웹 검색 | `langchain-community` `TavilySearchResults` |
| HTTP 클라이언트 | httpx (동기 `httpx.Client`) |
| 환경 변수 | python-dotenv (`.env`) |

---

## 2. 디렉터리 구조

```
cookmate_agent/
├── main.py                     # FastAPI 앱 생성, 헬스체크(GET /), uvicorn 실행 진입점
├── schemas.py                  # Pydantic 요청/응답 스키마 + Enum (Spring Boot 엔티티와 1:1 대응)
├── requirements.txt            # 의존성 목록
├── .env                        # API 키 (git 제외)
├── .gitignore
├── routers/
│   └── recipe.py               # /api/recipe 라우터 (Spring Boot의 @RequestMapping 역할)
└── agent/
    ├── graph.py                # 노드들을 연결해 LangGraph 파이프라인을 조립 (작성 예정)
    ├── recipe_agent.py         # State(RecipeState) 정의 + 그래프 노드 함수
    └── agent_method/           # 노드가 호출하는 "순수 서비스 로직" (외부 API / LLM 호출)
        ├── mfds_api.py         # 식약처 COOKRCP01 레시피 검색  → search_recipes_mfds()
        ├── tavily.py           # Tavily 웹 검색 + 블로그 노이즈 정제 → search_recipes_tavily()
        ├── spoonaculr_api.py   # Spoonacular 재료 기반 검색(영문) → 3단계 수집·병합·압축
        └── generate_recipe_llm.py  # LLM으로 RecipeResponse 구조화 생성 → generate_recipe_with_llm()
```

### 레이어별 책임

| 레이어 | 위치 | 책임 | 하지 말아야 할 것 |
|---|---|---|---|
| 앱 진입점 | `main.py` | `FastAPI` 객체 생성, 라우터 등록, 서버 실행 | 비즈니스 로직 |
| 라우터 | `routers/` | 요청 검증 → 초기 State 구성 → Agent `invoke` → 응답 반환 | 외부 API 직접 호출 |
| 스키마 | `schemas.py` | 요청/응답/Enum 정의, Spring Boot와의 계약 | 로직 포함 |
| Agent 그래프 | `agent/graph.py` | 노드 연결, 조건부 분기(평가 → 재시도) | 노드 내부 구현 |
| Agent 노드 | `agent/recipe_agent.py` | State에서 값을 꺼내 서비스 함수 호출, **변경된 키만 dict로 반환** | 외부 API 세부 구현 |
| 서비스 로직 | `agent/agent_method/` | 외부 API/LLM 호출 및 데이터 정제. LangGraph State를 모르는 순수 함수 | State 접근 |

### Agent State (`RecipeState`)

```python
class RecipeState(TypedDict):
    request: RecipeRequest        # 1단계: 요청
    raw_data: List[dict]          # 1단계: 외부 소스 검색 결과
    draft: RecipeResponse         # 2단계: LLM 초안
    eval_passed: bool             # 2단계: 평가 합격 여부
    feedback: str                 # 2단계: 불합격 시 수정 지시
    retry_count: int              # 2단계: 무한 루프 방지
    final_recipe: RecipeResponse  # 최종 산출물
```

계획된 파이프라인: **검색 노드(raw_data) → LLM 생성 노드(draft) → 평가 노드(eval_passed/feedback) → (불합격 & retry_count 미만이면 생성 노드로 회귀) → final_recipe**

---

## 3. API 계약 (Spring Boot ↔ FastAPI)

| Method | Path | 설명 | 상태 |
|---|---|---|---|
| GET | `/` | 헬스체크 `{"status": "UP", "service": "fastapi-ai-agent"}` | 동작 |
| POST | `/api/recipe/generate` | Agent로 레시피 생성 | 구현 중 |
| POST | `/api/recipe/generate/test` | 통신 테스트용 더미 응답 | 테스트용 |

**요청 `RecipeRequest`**
```json
{ "user_id": 1, "pantries": ["돼지고기", "김치"], "cuisines": ["한식"] }
```

**응답 `RecipeResponse`** — 필드명은 Spring Boot 엔티티와 맞추기 위해 **camelCase** 를 그대로 사용합니다.
```json
{
  "title": "김치찌개",
  "content": ["1. 김치를 볶습니다.", "2. 물을 넣고 끓입니다."],
  "source": "LangGraph AI Agent",
  "cookingTime": "30분",
  "level": "Level2",
  "cuisine": "한식",
  "recipeIngredients": [{ "name": "김치", "quantity": 200, "unit": "g" }]
}
```

Enum 값 (Spring Boot Enum과 반드시 동일하게 유지):
- `CuisineEnum`: 한식, 중식, 일식, 양식, 기타
- `LevelEnum`: Level0 ~ Level5
- `UnitEnum`: g, kg, ml, l, tsp, tbsp, cup, ea

> 스키마를 바꾸면 Spring Boot 쪽 DTO/Enum도 함께 바꿔야 합니다. 이 파일이 두 서버 간 계약입니다.

---

## 4. 빌드 & 실행

### 4.1 가상환경 및 의존성 설치

```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```
(macOS/Linux: `source venv/bin/activate`)

```bash
pip install -r requirements.txt
```

### 4.2 환경 변수 (`.env`, 프로젝트 루트)

```dotenv
OPENAI_API_KEY=...        # generate_recipe_llm.py (ChatOpenAI가 자동으로 읽음)
TAVILY_API_KEY=...        # tavily.py (TavilySearchResults가 자동으로 읽음)
MFDS_API_KEY=...          # mfds_api.py (식품안전나라 공공데이터 인증키)
SPOONACULAR_API_KEY=...   # spoonaculr_api.py
```

`.env`는 `.gitignore`에 포함되어 있으며 **절대 커밋하지 않습니다.** 새 키를 추가하면 이 목록도 갱신합니다.

### 4.3 서버 실행

```bash
python main.py
```
또는
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- 서버: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- 반드시 **프로젝트 루트에서** 실행합니다. 모든 import가 루트 기준 절대 경로(`from schemas import ...`, `from agent.agent_method...`)이기 때문입니다.

### 4.4 개별 모듈 단독 실행 (외부 API 확인용)

```bash
python -m agent.agent_method.spoonaculr_api
```

`if __name__ == "__main__":` 블록에서 샘플 입력으로 동작을 확인합니다. 별도 테스트 프레임워크는 아직 없습니다.

---

## 5. 규칙 & 컨벤션

### 5.1 네이밍

| 대상 | 규칙 | 예 |
|---|---|---|
| 파일/모듈 | snake_case | `mfds_api.py`, `generate_recipe_llm.py` |
| 함수/변수 | snake_case | `search_recipes_mfds`, `raw_data` |
| 클래스 / Pydantic 모델 | PascalCase | `RecipeRequest`, `RecipeState` |
| Enum | PascalCase + `Enum` 접미사 | `CuisineEnum`, `UnitEnum` |
| 상수 / 환경 변수 | UPPER_SNAKE_CASE | `MFDS_API_KEY` |
| LangGraph 노드 함수 | `<동작>_node` | `mfds_search_node`, `llm_generate_recipe_node` |
| 외부 검색 함수 | `search_recipes_<소스>` | `search_recipes_tavily` |
| 응답 스키마 필드 | **예외적으로 camelCase** (Spring Boot 호환) | `cookingTime`, `recipeIngredients` |
| 요청 스키마 필드 | snake_case | `user_id`, `pantries` |

### 5.2 코드 작성 규칙

- **노드와 서비스 로직 분리**: 노드(`recipe_agent.py`)는 State를 읽고 `agent_method`의 순수 함수를 호출한 뒤 **업데이트할 키만 dict로 반환**합니다. 반환 키는 반드시 `RecipeState`에 정의된 키여야 합니다.
- **스키마 우선**: 모든 Pydantic 필드에 `Field(description=...)`을 붙입니다. 이 description은 Swagger 문서이자 LLM `with_structured_output`의 지시문 역할도 합니다.
- **LLM 출력은 구조화 출력으로 강제**: `llm.with_structured_output(RecipeResponse)`를 사용하고 자유 텍스트 파싱은 하지 않습니다.
- **API 키는 코드에 하드코딩 금지**: `load_dotenv()` + `os.getenv()`로만 읽습니다.
- **외부 HTTP 호출**: `with httpx.Client() as client:` 컨텍스트로 열고, 실패 시 `raise_for_status()` 또는 빈 리스트/`None` 반환 중 하나로 모듈 내에서 일관되게 처리합니다.
- **LLM 입력 데이터는 정제 후 전달**: 이미지 URL, ID 등 불필요한 메타데이터와 블로그 노이즈를 제거해 토큰을 줄입니다 (`clean_recipe_text`, `optimize_recipe_data` 참고).
- **모듈 import 시 부작용 금지**: 테스트 호출 코드는 반드시 `if __name__ == "__main__":` 아래에 둡니다.
- **타입 힌트**: 함수 인자와 반환값에 타입 힌트를 작성합니다.
- **주석/docstring은 한국어**로, 함수 docstring에는 단계(1단계, 2단계…) 또는 처리 순서를 적습니다. Spring Boot 개념과 대응되는 부분은 주석으로 매핑을 남깁니다 (예: `# Spring Boot의 @RequestMapping("/api/recipe")`).
- 디버그 출력은 `pprint` / `print`를 사용 중이며, 운영 전 `logging`으로 교체합니다.

### 5.3 Git

- 브랜치: 현재 `main` 단일 브랜치.
- 커밋 메시지: **한국어**, 변경 내용을 한 줄로 요약 (예: `tavily search를 사용한 raw 레시피 검색`, `requirements 수정`). `d`, `별거 아닌거 수정`처럼 내용이 드러나지 않는 메시지는 지양합니다.
- 커밋 제외 대상: `.env`, `venv/`, `.venv/`, `__pycache__/`, `*.pyc`, `.vscode/`, `desktop.ini`(Windows 생성 파일 — `.gitignore`에 추가 권장).
- 새 패키지를 쓰면 `requirements.txt`에 카테고리 주석과 함께 추가합니다.

---

## 6. 현재 상태 & 알려진 이슈 (TODO)

코드 기준으로 확인된, 아직 동작하지 않거나 정리가 필요한 부분입니다.

| # | 위치 | 내용 |
|---|---|---|
| 1 | `main.py` | `routers/recipe.py`의 라우터가 **등록되지 않음** → `app.include_router(router)` 필요. 현재는 `/`만 응답 |
| 2 | `agent/graph.py` | 비어 있음. `StateGraph(RecipeState)`로 노드 연결 및 `compile()` 필요 |
| 3 | `routers/recipe.py` | `recipe_agent.invoke(...)` 호출 대상이 컴파일된 그래프가 아니라 모듈. `/generate`가 값을 반환하지 않음. 두 엔드포인트의 함수명이 `generate_recipe`로 중복 |
| 4 | `routers/recipe.py`, `agent/recipe_agent.py` | `from agent_method import ...` / `from agent.agent_method import search_recipes_mfds` — `__init__.py`가 없어 실패. `from agent.agent_method.mfds_api import search_recipes_mfds`로 수정 |
| 5 | `agent/recipe_agent.py` | `import pprint` 후 `pprint(...)` 호출 → `from pprint import pprint` 필요. 노드가 State에 없는 키(`pantries`, `mfds_data`, `llm_data`)를 사용 |
| 6 | `agent/agent_method/tavily.py` | 파일 하단 테스트 코드가 **import 시점에 실행**되어 API를 호출함 → `__main__` 블록으로 이동 |
| 7 | `agent/agent_method/mfds_api.py` | 재료를 `&`로 연결 — 식약처 API 파라미터 형식 확인 필요. `.env`에 `MFDS_API_KEY` 없음 |
| 8 | `routers/recipe.py` 테스트 API | 더미 응답이 스키마에 없는 `cost` 필드를 넘기고, `content`를 `List[str]`이 아닌 문자열로 넘김 |
| 9 | `generate_recipe_llm.py` | 프롬프트가 "한식 요리사"로 고정 — `cuisines` 요청값 반영 필요. 타입 힌트(`context_string: str`)와 실제 전달값(`List[dict]`) 불일치 |
| 10 | 전체 | 동기 함수(`httpx.Client`, `invoke`)를 `async def` 엔드포인트에서 호출 → 이벤트 루프 블로킹. `httpx.AsyncClient`/`ainvoke` 또는 일반 `def` 엔드포인트로 전환 고려 |
