import csv
from functools import lru_cache
import os
import re

from anyio import Path
import httpx
from dotenv import load_dotenv

from agent.agent_dto import FormattedRecipe
from agent.agent_method.ingredient_translator import _normalize_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MFDS_RECIPES_PATH = PROJECT_ROOT / "data" / "mfds_recipes.json"  
DICT_PATH = PROJECT_ROOT / "resources" / "ingredient_dictionary.csv"
_PREP_WORDS = re.compile(r"^(다진|깐|채썬|썬|삶은|데친|볶은|손질한|냉동|불린)")
_STAPLES = ["물", "소금", "설탕", "후추", "후춧가루", "식용유", "참기름", "간장"]


@lru_cache(maxsize=1)
def load_canonical_names() -> dict[str, str]:
    """
    {조회키: 대표 한국어 이름} (name_ko와 aliases_ko 모두 키)
    검증된 사전 사용
    """
    names: dict[str, str] = {}
    with open(DICT_PATH, encoding ="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = _normalize_key(row["name_ko"])
            names[key] = row["name_ko"]

            aliases = row["aliases_ko"].split("|")
            for alias in aliases:
                if alias:
                    names[_normalize_key(alias)] = row["name_ko"]
    return names
    




def search_recipes_mfds(pantries: list[str], number: int = 3) -> list[FormattedRecipe]:
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




