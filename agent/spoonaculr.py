import os
import httpx
from dotenv import load_dotenv
from pprint import pprint

# 환경 변수 로드
load_dotenv()
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

def search_by_ingredients(ingredients_list: list, number: int):
    """
    1단계: 보유한 재료 리스트를 받아 Spoonacular API로 레시피 기본 정보를 검색
    """
    url = "https://api.spoonacular.com/recipes/findByIngredients"
    ingredients_str = ",".join(ingredients_list)

    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "ingredients": ingredients_str, 
        "number": number,               
        "ranking": 1,                    
        "ignorePantry": True            
    }
    
    with httpx.Client() as client:
        response = client.get(url, params=params)
        
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error Code: {response.status_code}")
        return None

def search_recipe(recipe_ids: list, ingredients_map: dict):
    """
    2단계: 레시피 id 리스트로 조리 과정을 검색 1단계의 재료 정보를 하나로 병합
    """
    final_recipes = []

    with httpx.Client() as client:
        for recipe_id in recipe_ids:
            url = f"https://api.spoonacular.com/recipes/{recipe_id}/analyzedInstructions"
            params = {"apiKey": SPOONACULAR_API_KEY}

            response = client.get(url, params=params)
            
            if response.status_code == 200:
                instructions_data = response.json()
                
                recipe_detail = {
                    "recipe_id": recipe_id,
                    "instructions": instructions_data
                }

                if recipe_id in ingredients_map:
                    recipe_detail['title'] = ingredients_map[recipe_id]['title']
                    recipe_detail['missedIngredients'] = ingredients_map[recipe_id]['missedIngredients']
                    recipe_detail['usedIngredients'] = ingredients_map[recipe_id]['usedIngredients']
                
                final_recipes.append(recipe_detail)
            else:
                print(f"Error Code for ID {recipe_id}: {response.status_code}")

    return final_recipes

def optimize_recipe_data(raw_recipes: list):
    """
    3단계: 불필요한 메타데이터(이미지URL, ID 등)를 제거하고 LLM 프롬프트용 텍스트 최적화
    """
    optimized = []
    
    for recipe in raw_recipes:
        # 사용된 재료와 부족한 재료 텍스트만 추출
        used_ings = [ing['original'] for ing in recipe.get('usedIngredients', [])]
        missed_ings = [ing['original'] for ing in recipe.get('missedIngredients', [])]
        
        # 조리 과정 스텝 텍스트만 결합
        step_texts = []
        for instruction_group in recipe.get('instructions', []):
            for step_info in instruction_group.get('steps', []):
                step_texts.append(f"{step_info['number']}. {step_info['step']}")
                
        clean_data = {
            "recipe_name": recipe.get("title"),
            "recipe_id": recipe.get("recipe_id"),
            "used_ingredients": used_ings,
            "missed_ingredients": missed_ings,
            "instructions": "\n".join(step_texts)
        }
        optimized.append(clean_data)
        
    return optimized


# 메인
if __name__ == "__main__":
    # 검색할 영문 재료명 
    ingredients = ["pork", "kimchi"]
    number = 2

    # 1단계 재료 기반 레시피 id 검색 실행
    results = search_by_ingredients(ingredients, number)

    if results:
        # id를 기준으로 재료 정보 매핑 딕셔너리 생성 및 ID 리스트 추출
        ingredients_map = {}
        for recipe in results:
            recipe_id = recipe['id']
            ingredients_map[recipe_id] = {
                'title' : recipe['title'],
                'missedIngredients': recipe['missedIngredients'],
                'usedIngredients': recipe['usedIngredients']
            }

        recipe_id_list = [recipe['id'] for recipe in results]

        # 2단계 레시피 id로 레시피 검색
        final_results = search_recipe(recipe_ids=recipe_id_list, ingredients_map=ingredients_map)

        # LLM용 프롬프트 작성을 위한 텍스트
        optimized_results = optimize_recipe_data(final_results)

        # 최종 결과 출력
        pprint(optimized_results)