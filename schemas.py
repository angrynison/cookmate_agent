from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

# Spring Boot의 Cuisine Enum과 일치시킴
class CuisineEnum(str, Enum):
    한식 = "한식"
    중식 = "중식"
    일식 = "일식"
    양식 = "양식"
    기타 = "기타"

class LevelEnum(str, Enum):
    Level0 = "Level0"
    Level1 = "Level1"
    Level2 = "Level2"
    Level3 = "Level3"
    Level4 = "Level4"
    Level5 = "Level5"

class UnitEnum(str, Enum):
    g = "g"
    kg = "kg"
    ml = "ml"
    l = "l"
    tsp = "tsp"
    tbsp = "tbsp"
    cup = "cup"
    ea = "ea"

# RecipeIngredient Entity 대응 스키마
class RecipeIngredient(BaseModel):
    name: str = Field(description="재료명 (예: 돼지고기 목살)")
    quantity: int = Field(description="분량")
    unit: UnitEnum = Field(description="단위")

# AI 추천 요청 스키마 (Spring Boot -> FastAPI)
class RecipeRequest(BaseModel):
    user_id: int = Field(description="사용자 ID", default=1)
    pantries: List[str] = Field(description="보유 중인 재료 리스트")
    cuisines: Optional[List[CuisineEnum]] = Field(description="선호하는 요리 종류 (한식, 중식, 일식, 양식, 기타)", default=None)

# AI 추천 응답 스키마 (FastAPI -> Spring Boot)
class RecipeResponse(BaseModel):
    title: str = Field(description="레시피 제목")
    content: str = Field(description="조리 순서 및 상세 설명 (Spring Boot의 content 필드)")
    source: str = Field(description="출처 (예: LangGraph AI Agent / Tavily Search)")
    cookingTime: str = Field(description="조리 시간 (예: 20분)")
    level: LevelEnum = Field(description="난이도 (Level0~Level5)")
    cuisine: CuisineEnum = Field(description="요리 종류 (예: 한식, 중식)")
    recipeIngredients: List[RecipeIngredient] = Field(description="레시피에 사용된 재료 목록")