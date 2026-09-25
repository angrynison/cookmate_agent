from typing import Optional, TypedDict
from schemas import RecipeRequest, RecipeResponse

class RecipeAgentState(TypedDict):
    # 에이전트가 생각하는 동안 데이터를 담아둘 임시 메모장(재료 목록,검색 결과, 생성된 레시피 초안등)
    request: RecipeRequest  # 요청 정보
    search_context: Optional[str]
    final_recipe: Optional[RecipeResponse]  # 생성된 레시피 