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

def search_recipes_mfds(ingredients: list[str], number: int = 3) -> list[FormattedRecipe]:
    """
    오프라인 normazlied 된 mfds_recipes.json을 사용하여 재료 기반 레시피 검색
    """




# 정규식은 모듈 로드 시 한 번만 컴파일해서 재사용 
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




