import os
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from pprint import pprint
load_dotenv()

tavily_tool = TavilySearchResults(
    search_depth="advanced",
    include_answer = True
)

def search_recipes(query: str):
    results = tavily_tool.run(query)
    return results


query = "돼지고기 목살을 활용한 한식 레시피"
results = search_recipes(query)
pprint(results)