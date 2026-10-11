# 아래 node(메서드)들을 순서대로 연결하여 파이프라인으로 조립
from langgraph.graph import END, START, StateGraph

from agent.recipe_agent import RecipeState, mfds_search_node
from schemas import CuisineEnum


# 분기 판단 함수 (요리 종류 → 검색 소스 선택)
#    지금은 검색 노드가 식약처 하나뿐이라 그래프에 연결하지 않음
#    Spoonacular / Tavily 검색 노드를 추가할 때
#    builder.add_conditional_edges(START, route_by_cuisine) 로 연결할 예정
def route_by_cuisine(state: RecipeState) -> str:

    cuisines = state["request"].cuisines or []


    if not cuisines or CuisineEnum.한식 in cuisines:
        return "mfds_search"   

    # TODO: 양식 → "spoonacular_search", 그 외 → "tavily_search" (노드 추가 후)
    # 분기 함수는 모든 경우에 갈 곳을 반환해야 하므로, 지금은 기본값으로 식약처
    return "mfds_search"


# 그래프 정의 
builder = StateGraph(RecipeState)

# 노드 추가
builder.add_node("mfds_search", mfds_search_node)

# 노드 연결: START → mfds_search → END
builder.add_edge(START, "mfds_search")
builder.add_edge("mfds_search", END)


recipe_graph = builder.compile()


# 단독 실행 테스트: 프로젝트 루트에서 python -m agent.graph
if __name__ == "__main__":
    from schemas import RecipeRequest

    # 재료는 1개로 테스트 (search_recipes_mfds의 "&".join 문제로 2개 이상이면 첫 재료만 조건으로 쓰이거나 요청이 깨짐)
    initial_state = {"request": RecipeRequest(pantries=["돼지고기"])}

    final_state = recipe_graph.invoke(initial_state)

    candidates = final_state.get("recipe_candidates", [])
    print(f"후보 레시피 {len(candidates)}개")
    for candidate in candidates:
        names = [ingredient.name for ingredient in candidate.ingredients]
        print(f"- [{candidate.source.value} {candidate.source_id}] {candidate.title}")
        print(f"  재료: {', '.join(names)}")
        print(f"  단계 수: {len(candidate.steps)}")
