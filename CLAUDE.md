# CookMate Agent — 에이전트 지침

이 파일에는 **이 저장소에만 해당하는 규칙**만 둔다.
프로젝트 구조, 빌드 방법, 컨벤션은 아래 문서를 기준으로 한다.

@project.md

---

## 1. 학습·지도 방식

- 역할, 큰 그림, 챕터 나누기, 3단계 지도, 디버깅 지도 같은 **학습 규칙은 `dev-learning-mentor` 스킬 한 곳에서 관리**한다.
- 이 파일에 학습 규칙을 다시 쓰지 않는다. (두 곳에 쓰면 한쪽만 고쳐져서 충돌한다)
- 저장소 규칙(`project.md`)과 현업 관행이 다르면 차이를 설명하되 **저장소 규칙을 따르게** 한다.

## 2. 이 저장소에서 지도할 때 기준

- 새 모듈 위치: `project.md` 2장 "레이어별 책임" 표
  - 라우터 `routers/` → 그래프 `agent/graph.py` → 노드 `agent/recipe_agent.py` → 서비스 함수 `agent/agent_method/`
- 네이밍·코드 규칙: `project.md` 5장 / 알려진 문제: 6장
- 진행 중인 작업 맥락: Claude 프로젝트의 `cookmate_handoff.md` (이 저장소에는 없음. 저장소에 두려면 `docs/handoff.md`로 추가)
- 자주 보는 공식 문서
  - FastAPI: https://fastapi.tiangolo.com/ko/
  - Pydantic v2: https://docs.pydantic.dev/latest/
  - httpx: https://www.python-httpx.org/
  - LangChain·LangGraph 공식 문서
- 실행은 반드시 **프로젝트 루트에서** 한다. (import가 루트 기준 절대 경로)
