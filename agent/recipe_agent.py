# 실제 동작을 수행하는 개별 메서드들 노드로 정의 (Tavily 웹 검색 메서드, LLM에게 프롬프트 던지는 메서드)

from pprint import pprint
from typing import List, TypedDict

from agent.agent_method.generate_recipe_llm import generate_recipe_with_llm
from agent.agent_method.mfds_api import search_recipes_mfds,mfds_to_candidates
from agent.agent_dto import FormattedRecipeCandidate
from schemas import RecipeRequest, RecipeResponse

# State 정의 (미리 정의해둔 State)
class RecipeState(TypedDict):
    # 1단계 파이프라인: 레시피 검색
    request: RecipeRequest
    recipe_candidates: list[FormattedRecipeCandidate]


    # 2단계 파이프라인: eval -> 합격여부, feedback -> 불합격시 수정 지시사항, retry_count -> 무한루프 방지
    draft: RecipeResponse
    eval_passed: bool
    feedback: str
    retry_count: int

    # 최종 산출물
    final_recipe: RecipeResponse

# 식약처 검색 노드
def mfds_search_node(state: RecipeState):
    """
    1. State에서 재료(pantries) 리스트를 꺼낸다.
    2. 외부에 정의된 식약처 검색 로직을 실행한다.
    3. 검색 결과를 전처리한다
    4. State 업데이트
    """
    recipe_request = state["request"]
    pantries = recipe_request.pantries
    
    # Ministry of Food and Drug Safety (MFDS) 식약처 api Raw data 검색
    mfds_results = search_recipes_mfds(pantries)

    # 전처리
    recipe_candidates = mfds_to_candidates(mfds_results)

    # State 업데이트
    return {
        **state,
        "recipe_candidates": recipe_candidates
        }





def llm_generate_recipe_node(state: RecipeState):
    """
    1. State에서 raw_data를 꺼낸다.
    2. 외부에 정의된 LLM 레시피 생성 로직을 실행한다.
    3. 결과를 State의 'llm_data' 키에 담아 반환한다.
    """
    raw_data = state["raw_data"]
    
    # 순수 서비스 로직 호출
    llm_results = generate_recipe_with_llm(raw_data)
    pprint(f"LLM 레시피 생성 결과: {llm_results}")
    # State 업데이트
    return {"llm_data": llm_results}