import os
from langchain_openai import ChatOpenAI
from schemas import RecipeResponse # 작성해두신 Pydantic 스키마

def generate_recipe_with_llm(context_string: str) -> RecipeResponse:
    """
    수집된 검색 데이터를 바탕으로 LLM에게 레시피 생성을 지시하고,
    반드시 RecipeResponse 스키마에 맞는 결과만 반환하는 외부 메소드
    """
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    # 스키마를 강제
    structured_llm = llm.with_structured_output(RecipeResponse)
    
    # 3. 프롬프트 작성
    prompt = f"""
    당신은 전문 한식 요리사입니다. 
    아래 제공된 참고자료를 바탕으로 사용자가 쉽게 따라 할 수 있는 레시피를 작성해주세요.
    
    [참고자료]
    {context_string}
    """
    
    result = structured_llm.invoke(prompt)
    
    return result