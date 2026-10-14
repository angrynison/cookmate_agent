import os
import re

import httpx
from dotenv import load_dotenv

from agent.agent_dto import CandidateIngredient, FormattedRecipe, SourceEnum

load_dotenv()
MFDS_API_KEY = os.getenv("MFDS_API_KEY")


MFDS_BASE_URL = "http://openapi.foodsafetykorea.go.kr/api"
MFDS_SERVICE_ID = "COOKRCP01"
_MFDS_CODE_OK = "INFO-000"        # 정상 처리
_MFDS_CODE_NO_DATA = "INFO-200"   # 해당 데이터 없음 


def fetch_mfds_rows(start: int, end: int, timeout: float = 30.0) -> tuple[list[dict], int]:
    """
    식약처 레시피를 start번 ~ end번 구간만큼 가져온다
    """

    # api key가 없는경우 에러처리
    if not MFDS_API_KEY:
        raise RuntimeError("MFDS_API_KEY가 .env에 없습니다.")

    url = f"{MFDS_BASE_URL}/{MFDS_API_KEY}/{MFDS_SERVICE_ID}/json/{start}/{end}"

    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()   
    data = response.json()

    # api 응답 에러코드 저장
    body = data.get(MFDS_SERVICE_ID, data)
    result = body.get("RESULT", {})
    code = result.get("CODE")

    # 정상이 아니면 에러, 데이터 없음이면 빈 결과
    if code == _MFDS_CODE_NO_DATA:
        return [], 0
    if code != _MFDS_CODE_OK:

        raise RuntimeError(f"식약처 API 오류 [{code}] {result.get('MSG')}")

    rows = body.get("row", [])
    total = int(body.get("total_count", 0))  
    return rows, total


# Ministry of Food and Drug Safety (MFDS)
def search_recipes_mfds(pantries: list[str]) -> list[dict]:
    """
    MFDS(식약처) API를 사용하여 레시피를 검색
    """

    # 1. 재료 리스트를 쉼표(,)로 연결 
    pantry_str = "&".join(pantries)
    
    # 식약처 API URL 
    # /api/{인증키}/{서비스명}/{요청타입}/{시작}/{종료}/추가변수=값
    url = f"http://openapi.foodsafetykorea.go.kr/api/{MFDS_API_KEY}/COOKRCP01/json/1/3/RCP_PARTS_DTLS={pantry_str}"

    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()

    if response.status_code == 200:
        data = response.json()
        return data.get("COOKRCP01", {}).get("row", [])
    
    return []

# 정규식은 모듈 로드 시 한 번만 컴파일해서 재사용 
"""
parse_mfds_ingridients
재료를 나누는 구분자: 쉼표 또는 줄바꿈
예) 두부 320g(1모), 고추장 10g(2작은술, 다진 것) -> 고추장 10g(2작은술, 다진 것) 
괄호 안의 쉼표는 제외 → "고추장 10g(2작은술, 다진 것)" 같은 원문이 둘로 쪼개지는 문제 발생
예) 1. 고추장 10g(2작은술, 2. 다진 것)
,(?![^(]*\))  -> "기호 뒤쪽에 '(' 없이 ')'가 먼저 나오면(=괄호 안이면) 이 쉼표는 매칭하지 않음
"""
_SPLIT_PATTERN = re.compile(r",(?![^(]*\))|\n")

"""
_extrat_ingredient_name
분량이 시작되는 지점: 첫 숫자 또는 유니코드 분수(½ ⅓ ⅔ ¼ ¾)
"두부 320g(1모)" → "320" 앞에서 끊어서 "두부"만 남김
"""
_QUANTITY_START = re.compile(r"[\d½⅓⅔¼¾]")

"""
_extract_ingredient_name
숫자 없이 분량을 표현하는 말 → 이름에 섞이지 않도록 제거 ("소금 약간" → "소금")
"""
_VAGUE_AMOUNTS = ("약간", "적당량", "적당히", "조금")

"""
_extract_ingredient_name
일부 row에서 소제목 앞에 붙는 기호
"""
_BULLETS = "●•·-"

"""
_extract_steps
조리 단계 앞의 번호: "1. ", "10." 같은 패턴 구분
"""
_STEP_NUMBER = re.compile(r"^\s*\d+\s*\.\s*")

def _extract_ingredient_name(original: str) -> str:
    """
    second 구분
    재료 리스트에서 뽑아낸 한 블럭에서 매칭용 이름만 뽑음
    1단계: "●양념장 : 간장 10g"처럼 소제목이 붙어 있으면 콜론 뒤만 사용 -> 간장 10g
    2단계: 첫 숫자(분량) 앞까지 자르기 -> 간장
    3단계: 괄호 설명, "약간" 같은 말 제거
    """
    text = original.split(":")[-1]               # 콜론이 없으면 원문 그대로
    match = _QUANTITY_START.search(text)        # 두부 320g -> 두부
    name = text[: match.start()] if match else text   # 숫자가 없으면("소금 약간") 전체에서 정리
    name = name.split("(")[0]                    # "두부(국산)" → "두부"
    for word in _VAGUE_AMOUNTS:                  # 분량 표현하는 말 섞이지 않게 제거:소금 약간 -> 소금
        name = name.replace(word, "")

    return name.strip().strip(_BULLETS).strip()


def parse_mfds_ingredients(dtls: str) -> list[CandidateIngredient]:
    """
    first 구분
    RCP_PARTS_DTLS 문자열을 재료 하나하나(이름 + 원문)로 나눈다.
    1단계: 쉼표·줄바꿈으로 자르기 (괄호 안 쉼표는 유지) -> 정규식 호출
    2단계: 원문에서 이름 추출, 이름이 비면 재료로 보지 않음 -> extract_ingredient_name 함수 호출
    """
    if not dtls:
        return []

    # 반환용 list 정의
    ingredients: list[CandidateIngredient] = []

    # 2중 for문 정규식 호출
    for piece in _SPLIT_PATTERN.split(dtls):    # 리스트에서 재료들을 쉼표(,) 같은 기호로 구분
        original = piece.strip()                # 공백 제거
        if not original:                        # ",\n" 사이에서 생기는 빈 조각
            continue

        # extract_ingredient_name함수 호출
        name = _extract_ingredient_name(original) # 리스트에서 뽑은 재료 블럭에서 이름만 뽑아내기
        if not name:                             
            continue

        ingredients.append(CandidateIngredient(name=name, original=original))
    return ingredients


def extract_steps(row: dict) -> list[str]:
    """
    레시피 추출
    MANUAL01 ~ MANUAL20 중 내용이 있는 것만 순서대로 모으고 앞 번호("1. ")를 뗀다
    MANUAL 갯수는 정해져있음
    """
    steps: list[str] = []
    for i in range(1, 21):
        # f"{i:02d}" = 두 자리로 0 채우기 → MANUAL01, MANUAL02, ..., MANUAL20
        text = (row.get(f"MANUAL{i:02d}") or "").strip()
        # 비어있는것 PASS
        if not text:
            continue
        steps.append(_STEP_NUMBER.sub("", text))
    return steps


def mfds_to_candidates(rows: list[dict]) -> list[FormattedRecipe]:
    """
    LLM 입력을 위해 식약처 검색 결과 row 리스트를 DTO 리스트(Formatted 객체)로 변환
    1단계: 제목·재료·단계 추출
    2단계: 쓸 수 없는 row(제목 없음, 단계 없음) 제외
    3단계: 빈 문자열 필드는 None으로 통일해서 DTO 생성
    """
    candidates: list[FormattedRecipe] = []

    for row in rows:
        title = (row.get("RCP_NM") or "").strip()
        # 조리 단계 추출
        steps = extract_steps(row)
        # 재료 이름, 조리 단계가 없으면 스킵(쓸모가 없음)
        if not title or not steps:               
            continue

        # RCP_PARTS_DTLS 첫 줄에 요리 이름이 붙어 오는 row 대비: 제목과 같은 "재료"는 제외
        ingredients = [
            ing for ing in parse_mfds_ingredients(row.get("RCP_PARTS_DTLS", ""))
            if ing.name != title
        ]

        candidates.append(
            FormattedRecipe(
                title=title,
                ingredients=ingredients,
                steps=steps,
                # 값이 없으면 ""를 반환 → "값 없음"은 None 하나로 통일 (`or None`: 빈 문자열이면 None)
                tip=(row.get("RCP_NA_TIP") or "").strip() or None,
                source=SourceEnum.MFDS,
                source_id=row.get("RCP_SEQ") or None,
            )
        )
        
    return candidates



