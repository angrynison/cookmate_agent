from enum import Enum

from pydantic import BaseModel, Field


class SourceEnum(str, Enum):
    MFDS = "MFDS"                # 식약처 COOKRCP01
    SPOONACULAR = "SPOONACULAR"  # Spoonacular API
    TAVILY = "TAVILY"            # Tavily 웹 검색

# 재료 1개 = 이름 + 원문 (Spring의 @Embeddable)
class CandidateIngredient(BaseModel):
    name: str = Field(description="매칭·점수 계산용 재료 이름 (예: 두부)")
    original: str = Field(description="LLM에 넘길 분량 포함 재료 원문 (예: 두부 320g(1모))")


class FormattedRecipeCandidate(BaseModel):
    title: str = Field(description = "레시피 제목")
    ingredients: list[CandidateIngredient] = Field(description = "레시피에 포함된 재료 목록 (이름 + 원문)")
    steps: list[str] = Field(description = "조리 순서 및 레시피 상세 설명")
    raw_text: str | None = Field(default = None, description = "비정형 Raw Data를 위한 필드")
    tip: str | None = Field(default = None, description = "레시피 팁")
    url: str | None = Field(default = None, description = "레시피 출처")

    source: SourceEnum = Field(description="후보 레시피를 가져온 검색 소스")
    # 식약처 RCP_SEQ, Spoonacular id처럼 원본을 다시 찾을 수 있는 키 (Tavily는 고유 ID가 없으므로 None, url로 대체)
    # RCP_SEQ는 문자열("137"), Spoonacular id는 숫자(73420)라서 하나로 맞추기 위해 str로 저장
    source_id: str | None = Field(default=None, description="원본 데이터의 고유 ID (식약처 RCP_SEQ, Spoonacular id)")
