# 아래 node(메서드)들을 순서대로 연결하여 파이프라인으로 조립
from langgraph.graph import END, START, StateGraph

from agent.recipe_agent import RecipeState, translate_node, mfds_node, spoonacular_node, tavily_node, ranking_candidates_node
from schemas import CuisineEnum


# 분기 판단 함수 (요리 종류 → 검색 소스 선택)
#    지금은 검색 노드가 식약처 하나뿐이라 그래프에 연결하지 않음
#    Spoonacular / Tavily 검색 노드를 추가할 때
#    builder.add_conditional_edges(START, route_by_cuisine) 로 연결할 예정
def route_by_cuisine(state: RecipeState) -> str:
    cuisines = state["request"].cuisines or []

    if not cuisines or CuisineEnum.한식 in cuisines:
        return "mfds_node"   

    if not cuisines or CuisineEnum.양식 in cuisines:
        return "translate_node"

    if not cuisines or CuisineEnum.기타 in cuisines:
        return "tavily_node"

    return "translate_node"


# 그래프 정의 
builder = StateGraph(RecipeState)

# 노드 추가
builder.add_node("mfds_node", mfds_node)
builder.add_node("translate_node", translate_node)
builder.add_node("spoonacular_node", spoonacular_node)
builder.add_node("tavily_node", tavily_node)
builder.add_node("ranking_candidates", ranking_candidates_node)

"""
이후 
llm generate_recipe 노드 추가
레시피 적절한지 평가하는 노드 추가 (vector DB 검색)
END 노드 추가
"""


# 분기 판단 함수 연결
builder.add_conditional_edges(START, route_by_cuisine) 
# 번역이 필요한 api는 번역 -> 검색 노드 연결
builder.add_edge("translate_node", "spoonacular_node")
# 식약처 검색 노드 연결
builder.add_edge("mfds_node", "ranking_candidates")
# spoonacular 검색 노드 추가 후 연결
builder.add_edge("spoonacular_node", END)
# tavily 검색 노드 추가 후 연결
builder.add_edge("tavily_node", "ranking_candidates")

recipe_graph = builder.compile()


# 단독 실행 테스트
if __name__ == "__main__":
    from schemas import RecipeRequest

    # 재료는 1개로 테스트 
    initial_state = {"request": RecipeRequest(pantries=["돼지고기", "대파", "양파", "고추가루"], cuisines=[CuisineEnum.양식])}
    final_state = recipe_graph.invoke(initial_state)
    candidates = final_state.get("recipe_candidates") or []
    print("번역:", final_state.get("translated_ingredients"))
    print(f"후보 {len(candidates)}개")
    for recipe in candidates:
        names = [ingredient.name for ingredient in recipe.ingredients]
        print(f"- [{recipe.source.value} {recipe.source_id}] {recipe.title}")
        print(f"  재료 {len(names)}개: {', '.join(names)}")
        print(f"  단계 {len(recipe.steps)}개 | {recipe.url}")

