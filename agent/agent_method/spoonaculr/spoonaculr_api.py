import json
from pathlib import Path
import os
import httpx
from dotenv import load_dotenv

from agent.agent_dto import FormattedRecipe, SourceEnum, CandidateIngredient

# 환경 변수 로드
load_dotenv()
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

# 테스트용 저장json
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "spoonacular_raw.json"


class SpoonacularApiError(RuntimeError):
    """Spoonacular 호출 실패 (키 없음, 연결 실패, 4xx/5xx). 노드·호출하는 쪽이 다른 예외와 구분할 수 있게"""


def download_test_recipe() -> list[dict]:
    """
    Spoonacular API에서 테스트용 레시피 Raw data를 가져와서 data/spoonacular_raw.json에 저장(test용)
    """
    test_ingredients = ["pork", "kimchi"]
    number = 2
    url = "https://api.spoonacular.com/recipes/complexSearch"
    ingredients_str = ",".join(test_ingredients)

    params = {
        "includeIngredients": ingredients_str,
        "fillIngredients": True,
        "sort": "max-used-ingredients",
        "ignorePantry": True,
        "number": number,
        "instructionsRequired": True,
        "addRecipeInformation": True,
        "RequireInstructions": True,
        "apiKey": SPOONACULAR_API_KEY
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)  

    with httpx.Client() as client:
        response = client.get(url, params=params)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(response.json(), f, ensure_ascii=False, indent=2)


def search_recipes_spoonaculr(ingredients: list[str], number: int) -> dict:
    """
    Spoonacular API를 사용하여 재료 기반 레시피 검색
    성공하면 응답 전체(dict: results, offset, number, totalResults), 실패하면 SpoonacularApiError
    """
    # 키가 없으면 요청을 보내지 않는다 (보내 봐야 401만 돌아옴)
    if not SPOONACULAR_API_KEY:
        raise SpoonacularApiError("SPOONACULAR_API_KEY가 .env에 없습니다")

    url = "https://api.spoonacular.com/recipes/complexSearch"
    ingredients_str = ",".join(ingredients)

    """
    sort -> "max-used-ingredients" 사용된 재료가 많은 순으로 정렬, "min-missed-ingredients"로 설정하면 부족한 재료가 적은 순으로 정렬
    ignorePantry -> True로 설정하면 기본재료(소금, 후추 등)는 있다고 생각
    instructionsRequired -> True로 설정하면 조리법이 있는 레시피만 검색
    """
    
    params = {
        "includeIngredients": ingredients_str,
        "fillIngredients": True,
        "sort": "max-used-ingredients",
        "ignorePantry": True,
        "number": number,
        "instructionsRequired": True,
        "addRecipeInformation": True,
        "RequireInstructions": True,
        "apiKey": SPOONACULAR_API_KEY
    }

    try:
        # timeout: 응답이 멈춰도 요청(노드)이 무한정 기다리지 않게
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
    except httpx.RequestError as e:   # 타임아웃·연결 실패
        raise SpoonacularApiError(f"Spoonacular 연결 실패: {type(e).__name__}") from e

    # raise_for_status()는 오류 메시지에 요청 URL(apiKey 포함)을 넣으므로, 키가 로그에 남지 않게 상태 코드만 남긴다
    if response.status_code != 200:
        raise SpoonacularApiError(f"Spoonacular 응답 오류: HTTP {response.status_code}")

    return response.json()


def is_valid_recipe(row: dict) -> bool:
    """
    FormattedRecipe로 만들 수 있는 레시피인지 확인 (id·제목·재료·조리 단계가 모두 있어야 함)
    """
    if not row:
        return False
    if not row.get("id") or not row.get("title") or not row.get("extendedIngredients") or not row.get("analyzedInstructions"):
        return False
    return True


def load_raw_rows(path: Path) -> dict:
    """저장해 둔 응답 파일 전체를 읽는다 (레시피 목록은 "results" 키 아래에 있음)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def print_normalized_recipe(recipe: list[FormattedRecipe]) -> None:
    """
    FormattedRecipe를 보기 좋게 출력
    """
    for recipe in recipe:
        print(f"Title: {recipe.title}")
        print(f"URL: {recipe.url}")
        print(f"Tip: {recipe.tip}")
        print("Ingredients:")
        for ingredient in recipe.ingredients:
            print(f"  - Name: {ingredient.name}, Original: {ingredient.original}")
        print("Steps:")
        for i, step in enumerate(recipe.steps, start=1):
            print(f"  {i}. {step}")


def normalize_spoonaculr_data(raw_recipes: list[dict]) -> list[FormattedRecipe]:
    """
    Spoonacular API의 Raw data를 FormattedRecipe로 변환
    """
    formatted_recipes: list[FormattedRecipe] = []
    
    for row in raw_recipes:

        if not is_valid_recipe(row):
            print(f"Invalid data: {row.get('title', 'Unknown Title')}")
            continue

        title = row.get("title")

        # 레시피 추출
        steps = []
        for instructions in row.get("analyzedInstructions", []):
            for step in instructions.get("steps", []):
                steps.append(step.get("step", ""))

        # 재료 추출
        ingredients: list[CandidateIngredient] = []
        for extended_ingredients in row.get("extendedIngredients", []):
            name = extended_ingredients.get("name")
            original = extended_ingredients.get("original")
            if name and original:
                ingredients.append(CandidateIngredient(name=name, original=original))

        # FormattedRecipe 생성
        formatted_recipes.append(FormattedRecipe(
            title=title,
            ingredients=ingredients,
            steps=steps,
            raw_text=None,
            tip=None,
            url=row.get("sourceUrl"),
            source=SourceEnum.SPOONACULAR,
            source_id=str(row["id"]),   # Spoonacular id는 숫자 → 식약처 RCP_SEQ와 맞춰 str로 저장
        ))


    return formatted_recipes


def search_spoonacular_candidates(ingredients: list[str], number: int = 3) -> list[FormattedRecipe]:
    """
    재료로 Spoonacular를 검색해 공통 후보 형식(FormattedRecipe)으로 돌려준다 (그래프 노드가 부르는 진입 함수)
    1단계: API 검색 (실패하면 SpoonacularApiError)
    2단계: 응답에서 레시피 목록(results) 꺼내기
    3단계: FormattedRecipe로 변환
    number: 받아 올 레시피 수. 결과 1건마다 포인트가 붙으므로 작게 유지
    """
    response = search_recipes_spoonaculr(ingredients, number)
    rows = response.get("results", [])
    return normalize_spoonaculr_data(rows)


# 메인
def main() -> None:
    """
    저장해 둔 응답 파일로 변환 결과를 확인한다 (API 호출 없음, 디버깅용)
    """
    # 파일 전체(dict)에서 레시피 목록만 꺼낸다
    saved_response = load_raw_rows(OUTPUT_PATH)
    rows = saved_response.get("results", [])

    # FormattedRecipe로 변환
    formatted_recipes = normalize_spoonaculr_data(rows)

    # 결과 출력
    print(f"변환된 레시피 {len(formatted_recipes)}건")
    print_normalized_recipe(formatted_recipes)


if __name__ == "__main__":
    main()
