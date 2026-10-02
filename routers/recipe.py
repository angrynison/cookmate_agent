from fastapi import APIRouter
from agent import recipe_agent
from agent.agent_method import search_recipes_mfds
from schemas import (
    RecipeIngredient,
    LevelEnum, 
    CuisineEnum,
    RecipeRequest, 
    RecipeResponse,
    UnitEnum
)

# Spring Boot의 @RequestMapping("/api/recipe")
router = APIRouter(
    prefix="/api/recipe",
    tags=["Recipe"]
)

# response_model을 지정하면 FastAPI가 자동으로 JSON 응답을 해당 스키마에 맞춰 검증하고 포맷팅
# 수정 필요 ai agent만 호출하면됨
@router.post("/generate", response_model=RecipeResponse)
async def generate_recipe(request: RecipeRequest):
    """
    Spring Boot 서버로부터 요청받아 식품의약처 한식 레시피를 생성 
    """
    initial_State = {
        "pantries": request.pantries,
        "raw_data": [],
        "llm_data": None,
        "final_recipe": None
    }

    final_State = recipe_agent.invoke(initial_State)
    final_data = final_State.get("final_recipe", {})

    









# 테스트 api
@router.post("/generate/test", response_model=RecipeResponse)
async def generate_recipe(request: RecipeRequest):
    """
    Spring Boot 서버로부터 요청받아 레시피를 생성 추후 수정 예정
    (현재는 통신 테스트를 위한 더미 데이터 반환)
    """
    
    print(f"요청받은 사용자 ID: {request.user_id}")
    print(f"받은 재료 리스트: {request.pantries}")

    pantires = request.pantries

    dummy_response = RecipeResponse(
        title="AI 추천 김치찌개",
        content="1. 김치를 볶습니다.\n2. 물을 넣고 끓입니다.\n3. 돼지고기를 넣습니다.",
        source="LangGraph AI Agent",
        cost=8500,
        cookingTime="30분",
        level=LevelEnum.Level2,
        cuisine=CuisineEnum.한식,
        recipeIngredients=[
            RecipeIngredient(name="김치", quantity=200, unit=UnitEnum.g),
            RecipeIngredient(name="돼지고기", quantity=150, unit=UnitEnum.g)
        ]
    )
    
    return dummy_response