import csv
import threading
from functools import lru_cache
from pathlib import Path
from pprint import pprint

import openai

from agent.agent_method.ingredient_translator_llm import IngredientTranslationError, translate_with_llm

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DICT_PATH = PROJECT_ROOT / "resources" / "ingredient_dictionary.csv"
PENDING_PATH = PROJECT_ROOT / "resources" / "ingredient_pending.csv"

DICT_FIELDS = ["name_ko", "name_en", "aliases_ko", "aliases_en", "source", "verified"]

# 서버는 요청 여러 개를 동시에 처리한다 → pending 파일 쓰기와 메모리 사전 추가를 한 번에 하나씩만
_pending_lock = threading.Lock()


def _normalize_key(text: str) -> str:
    """비교용 키: 공백·줄바꿈을 모두 지운다 (" 청양 고추 " → "청양고추")"""
    # strip()은 앞뒤 공백만 지워서 "청양 고추"처럼 가운데 공백이 있으면 사전의 "청양고추"와 달라진다
    return "".join(text.split())


# 사전 전체를 캐시에 올려둠, 두번째 호출부터는 즉시 반환할 수 있도록
@lru_cache(maxsize=1)
def _load_dictionary() -> dict[str, str]:
    """
    CSV를 한 번만 읽어 {조회키: name_en}으로 만든다 조회키를 name_ko와 aliases_ko를 모두 키로 넣어서 입력 범용성을 높임
    본 프로젝튼에 영어 사전은 2개가 있는데 신뢰도가 높은 ingredient_dictionary.csv 파일을 우선시 한다
    """
    lookup: dict[str, str] = {}
    for path in (DICT_PATH, PENDING_PATH):
        if not path.exists():   # pending 파일은 첫 LLM 번역 전까지 없다
            continue
        # utf-8-sig: 엑셀용 BOM을 떼고 읽는다 (그냥 utf-8이면 첫 칸 이름이 "﻿name_ko"가 돼서 KeyError)
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                key = _normalize_key(row["name_ko"])    # dict[돼지고기,null] , dict[베이컨,null]
                if path == PENDING_PATH and key in lookup:   # 검토된 본 사전이 우선
                    continue
                lookup[key] = row["name_en"]            # dict[돼지고기,pork] , dict[베이컨,bacon]

                alias_list = row["aliases_ko"].split("|")
                for alias in alias_list:
                    if alias:   # 빈 칸이면 "".split("|") == [""] → 빈 문자열이 키가 되지 않게 건너뜀
                        lookup[_normalize_key(alias)] = row["name_en"] # dict[돈육,pork] , dict[돼지pork]
    return lookup


def lookup_ingredients(pantries: list[str]) -> tuple[dict[str, str], list[str]]:
    """
    사용자 입력재료들을 받음 -> 사전을 뒤져서 있는것,없는것 반환
    """

    dictionary = _load_dictionary()
    found: dict[str, str] = {}
    missing: list[str] = []
    for pantry in pantries:
        key = _normalize_key(pantry)
        if not key:
            continue
        if key in dictionary:
            found[pantry] = dictionary[key]   
        elif pantry not in missing:
            missing.append(pantry)
    return found, missing


def _save_pending(translated: dict[str, str]) -> None:
    """
    LLM 번역 결과를 검토 대기 파일에 한 줄씩 이어 쓰고 
    메모리 사전(dict 캐시)에도 바로 넣는다 같은 내용에 대해 llm 호출을 2번하지 않기 위해
    """
    with _pending_lock:
        is_new_file = not PENDING_PATH.exists()
        # "a": 기존 줄을 지우지 않고 뒤에 이어 쓴다. utf-8-sig여도 BOM은 파일 맨 앞에 한 번만 들어간다
        with open(PENDING_PATH, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=DICT_FIELDS)
            if is_new_file:   # 헤더는 파일을 처음 만들 때만
                writer.writeheader()
            for name_ko, name_en in translated.items():
                writer.writerow({
                    "name_ko": name_ko,
                    "name_en": name_en,
                    "aliases_ko": "",       
                    "aliases_en": "",
                    "source": "llm",
                    "verified": "false",    # 검토 전이므로 항상 false, 검토 후 추후 Merge
                })

        dictionary = _load_dictionary()   # @lru_cache라 매번 같은 dict 객체 → 여기 넣으면 다음 조회에 보인다
        for name_ko, name_en in translated.items():
            dictionary[_normalize_key(name_ko)] = name_en


def translate_ingredients(pantries: list[str]) -> list[str]:

    found, missing = lookup_ingredients(pantries)

    if missing:
        try:
            translated = translate_with_llm(missing)
        # 번역을 못 해도 사전에서 찾은 재료로는 검색할 수 있다 → 요청 전체를 실패시키지 않는다
        except (IngredientTranslationError, openai.OpenAIError) as e:
            print(f"[재료 번역] LLM 실패, 사전 결과만 사용: {type(e).__name__}: {e}")
            translated = {}

        if translated:
            _save_pending(translated)
            found.update(translated)

    pantries_en: list[str] = []
    for pantry in pantries:
        name_en = found.get(pantry)
        if name_en and name_en not in pantries_en:   # "대파"와 "파"가 둘 다 green onion이어도 검색어는 한 번만
            pantries_en.append(name_en)
    return pantries_en


def main() -> None:
    pantries = ["돼지고기", "쇠고기", " 대파 ", "청양 고추", "샬롯", "", "호박", "샬롯"]

    found, missing = lookup_ingredients(pantries)
    print("찾은 것:")
    pprint(found)
    print("못 찾은 것:")
    pprint(missing)

    # 실제 LLM 호출: 1번째는 못 찾은 재료(샬롯, 호박)를 LLM에 묻고, 2번째는 사전(메모리)에서 끝나야 한다
    print("1번째:", translate_ingredients(pantries))
    print("2번째:", translate_ingredients(pantries))


if __name__ == "__main__":
    main()
