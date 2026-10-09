# 실제 동작을 수행하는 개별 메서드들 노드로 정의 (Tavily 웹 검색 메서드, LLM에게 프롬프트 던지는 메서드)

import pprint
from typing import List, TypedDict

from agent.agent_method.generate_recipe_llm import generate_recipe_with_llm
from agent_method import search_recipes_mfds
from schemas import RecipeRequest, RecipeResponse

# State 정의 (미리 정의해둔 State)
class RecipeState(TypedDict):
    # 1단계 파이프라인: 레시피 검색
    request: RecipeRequest
    raw_data: List[dict]  

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
    3. 결과를 State의 'mfds_data' 키에 담아 반환한다.
    """
    pantries = state["pantries"]
    
    # 순수 서비스 로직 호출
    mfds_results = search_recipes_mfds(pantries)
    pprint(f"식약처 검색 결과: {mfds_results}")
    # State 업데이트
    return {"mfds_data": mfds_results}

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