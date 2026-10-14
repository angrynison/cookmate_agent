import os
import re
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from pprint import pprint
load_dotenv()

# LLM용 프롬프트 작성을 위한 텍스트 압축 진행
def clean_recipe_text(text: str) -> str:
    if not text:
        return ""
        
    # 1단계: '재료' 키워드를 기준으로 서론 잘라내기
    start_idx = text.find("재료")
    if start_idx != -1:
        safe_start = max(0, start_idx - 50)
        text = text[safe_start:]

    # 2단계: 연속된 줄바꿈과 공백을 1개로 압축
    text = re.sub(r'\n{2,}', '\n', text)
    text = re.sub(r'\s{2,}', ' ', text)
    
    # 3단계: 불필요한 블로그 노이즈 단어 제거
    noise_words = [
        "본문 바로가기", "카테고리 이동", "블로그", "서로이웃", "이웃환영", 
        "좋아요", "구독", "프로필", "공감", "댓글", "저작자표시", "반응형"
    ]
    for word in noise_words:
        text = text.replace(word, "")
        
    return text.strip()

# tavily 파라미터 적용 도메인 제외 적용
tavily_tool = TavilySearchResults(
    max_results=1,
    search_depth="advanced",
    include_answer=True,
    exclude_domains=["instagram.com", "facebook.com"]
)

def search_recipes_tavily(query: str):
    results = tavily_tool.run(query)
    
    # 검색된 결과 리스트를 순회하며 content 값만 전처리 함수로 정제
    for result in results:
        if 'content' in result:
            result['content'] = clean_recipe_text(result['content'])
            
    return results

query = "파스타,마늘,페퍼론치노,바지락을 활용한 레시피"
results = search_recipes_tavily(query)
pprint(results)