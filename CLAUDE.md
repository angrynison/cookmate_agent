# CookMate Agent — 에이전트 지침

이 파일에는 **이 저장소에만 해당하는 규칙**만 둔다.
프로젝트 구조, 빌드 방법, 컨벤션은 아래 문서를 기준으로 한다.

@project.md

---

## 1. 학습·지도 방식

- 역할, 큰 그림, 챕터 나누기, 3단계 지도, 디버깅 지도 같은 **학습 규칙은 `dev-learning-mentor` 스킬 한 곳에서 관리**한다.
- 이 파일에 학습 규칙을 다시 쓰지 않는다. (두 곳에 쓰면 한쪽만 고쳐져서 충돌한다)
- 저장소 규칙(`project.md`)과 현업 관행이 다르면 차이를 설명하되 **저장소 규칙을 따르게** 한다.

## 1-1. 학습 루프 (cowork 연결)

- 이 저장소에서 일할 때도 학습 루프를 돌린다. 기억·스킬·일지는 **cowork 폴더**에 읽고 쓰고, 이 저장소에는 만들지 않는다.
- 절차 원본: `C:\Users\kalin\cowork\LOOP.md` (Cowork 셸에서는 `$HOME/mnt/cowork/LOOP.md`)
- Claude Code 는 아래 줄로 불러온다. 처음 한 번 "외부 import 승인" 창이 뜨면 허용한다.

@~/cowork/LOOP.md

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

## 3. 스킬 우선순위

여러 스킬의 규칙이 부딪히면 이 절을 따른다. (`using-superpowers`의 "1%라도 관련 있으면 스킬 호출" 규칙보다 우선한다)

- **학습 모드**(기본값)에서는 `dev-learning-mentor`가 superpowers 스킬보다 우선한다.
- 아래 스킬은 **작업 모드이거나 사용자가 이름을 들어 직접 요청할 때만** 쓴다.
  - `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:executing-plans`, `superpowers:subagent-driven-development`, `superpowers:test-driven-development`
  - 이유: 설계 문서 작성, 계획 연속 실행, Claude가 직접 테스트·구현을 쓰는 흐름이 "챕터 하나씩, 사용자가 직접 짠다"는 학습 방식과 맞지 않는다.
- 아래 스킬은 Claude의 **내부 점검용**으로만 쓰고, 답변 형식은 `dev-learning-mentor`를 따른다.
  - `superpowers:systematic-debugging`: 원인 조사는 이 스킬대로 하고, 사용자에게는 멘토 스킬 10장 순서(힌트 중심, 두 답변으로 나눔)로 전달한다.
  - `superpowers:verification-before-completion`: "됐다"고 말하기 전에 실행해서 확인한다.
- `karpathy-guidelines`는 멘토 스킬의 "최소 버전 먼저"와 같은 방향이므로 그대로 함께 쓴다.
