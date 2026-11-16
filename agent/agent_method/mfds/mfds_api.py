import csv
import re
import json
from functools import lru_cache
from pathlib import Path
from agent.agent_dto import FormattedRecipe
from agent.agent_method.ingredient_translator import _normalize_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MFDS_RECIPES_PATH = PROJECT_ROOT / "data" / "mfds_recipes.json"  
DICT_PATH = PROJECT_ROOT / "resources" / "ingredient_dictionary.csv"
_PREP_WORDS = re.compile(r"^(다진|채썬|썬|삶은|데친|볶은|손질한|냉동|불린)")
_STAPLES = ["물", "소금", "설탕", "후추", "후춧가루", "식용유", "참기름", "간장"]

@lru_cache(maxsize=1)
def load_canonical_names() -> dict[str, str]:
    """
    검증된 사전에 있는 재료 이름(name_ko, aliases_ko)을 key로 사용
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
    
def _ingredient_key(name: str) -> str:
    """
    사용자가 입력한 재료 이름을 사전 조회용 키로 변환
    """

    key = _normalize_key(name)
    key = _PREP_WORDS.sub("", key)
    return load_canonical_names().get(key, key)  

@lru_cache(maxsize=1)
def load_mfds_recipes() -> list[FormattedRecipe]:
    """
    Local에 저장된 MFDS 레시피 JSON 파일을 로드
    """
    formatted_recipes: list[FormattedRecipe] = []
    with open(MFDS_RECIPES_PATH, encoding="utf-8") as f:
        data = json.load(f)
        for row in data:
            formatted_recipes.append(FormattedRecipe.model_validate(row))
    return formatted_recipes

def search_recipes_mfds(pantries: list[str], number: int = 5) -> list[FormattedRecipe]:
    """
    오프라인 normazlied 된 mfds_recipes.json을 사용하여 재료 기반 레시피 검색
    """
    staples = {_ingredient_key(item) for item in _STAPLES}
    my_keys = {_ingredient_key(item) for item in pantries} - staples

    formatted_recipes = load_mfds_recipes()

    scored = []
    for recipe in formatted_recipes:
        keys = {_ingredient_key(item.name) for item in recipe.ingredients}  
        recipe_keys = keys - staples
        matched = len(my_keys.intersection(recipe_keys))
        if matched == 0:
            continue
        missing = len(recipe_keys - my_keys)
        scored.append((matched, missing, recipe))

    scored.sort(key=lambda item: (-item[0], item[1]))  

    return [recipe for _, _, recipe in scored[:number]]  # 상위 number개 레시피 반환





        


if __name__ == "__main__":
    # 테스트용
    name = ["물", "소금", "설탕", "후추", "후춧가루", "식용유", "참기름", "간장", "다진마늘", "채썬양파", "삶은계란"]
    searched_recipe = search_recipes_mfds(name, number=5)
    for recipe in searched_recipe:
        print(recipe.title, len(recipe.ingredients))
        print(recipe.steps)


