from enum import Enum

from pydantic import BaseModel, Field


class SourceEnum(str, Enum):
    MFDS = "MFDS"                # 식약처 COOKRCP01
    SPOONACULAR = "SPOONACULAR"  # Spoonacular API
    TAVILY = "TAVILY"            # Tavily 웹 검색


# 재료 1개 = 이름 + 원문 (+ 소제목) (Spring의 @Embeddable)
# 정규화 LLM 출력틀
class CandidateIngredient(BaseModel):
    name: str = Field(
        description=(
            "보유 재료와 매칭할 재료 이름만. "
            "분량·단위·괄호 설명·소제목·'약간' 같은 말과 손질 표현(다진, 채 썬, 삶은)은 뺀다. "
            "원문 표기는 바꾸지 않는다(쇠고기를 소고기로 바꾸지 않음). "
            "예: '●양념장 : 간장 10g(2작은술)' → '간장', '다진 마늘 5g' → '마늘'"
        )
    )
    original: str = Field(
        description=(
            "원문에서 이 재료에 해당하는 부분을 글자 하나 바꾸지 않고 그대로 복사한 것. "
            "분량은 포함하고, 앞에 붙은 소제목과 '<br>' 같은 태그는 뺀다. "
            "예: '●양념장 : 간장 10g(2작은술)' → '간장 10g(2작은술)'"
        )
    )
    
    group: str | None = Field(
        default=None,
        description=(
            "이 재료가 속한 소제목(예: 주재료, 양념장, 육수). "
            "소제목은 다음 소제목이 나올 때까지 뒤 재료들에도 이어진다. "
            "소제목이 없으면 null. '[ 2인분 ]' 같은 인분 표시는 소제목이 아니다"
        ),
    )


# 정규화 LLM 출력 전용 모델 (normalize_rawdata_llm.py의 with_structured_output에 넘긴다)
# - with_structured_output의 최상위는 객체여야 해서 list[CandidateIngredient]를 한 번 감싼다
class NormalizedIngredients(BaseModel):
    """식약처 재료 문자열(RCP_PARTS_DTLS)을 재료 하나 단위로 나눈 결과"""

    ingredients: list[CandidateIngredient] = Field(
        description=(
            "원문에 나온 순서대로 모든 재료. "
            "한 조각 안에 재료가 두 개 있으면 둘로 나눈다. "
            "소제목만 있는 조각, 요리 이름, 인분 표시는 재료가 아니므로 넣지 않는다. "
            "원문의 재료를 빠뜨리거나 원문에 없는 재료를 추가하지 않는다"
        )
    )


# mfds_recipes.json 한 건의 저장 형태로 레시피 생성을 위한 LLM 응답 형식임
# ingredients는 전처리 가공이 어려워 normalized_LLM 실행결과 형식(NormalizedIngredients)에서 받아 코드에서 조립한다
class FormattedRecipe(BaseModel):
    title: str = Field(description = "레시피 제목")
    ingredients: list[CandidateIngredient] = Field(description = "레시피에 포함된 재료 목록 (이름 + 원문 + 소제목)")
    steps: list[str] = Field(description = "조리 순서 및 레시피 상세 설명")
    raw_text: str | None = Field(default = None, description = "비정형 Raw Data를 위한 필드")
    tip: str | None = Field(default = None, description = "레시피 팁")
    url: str | None = Field(default = None, description = "레시피 출처")

    source: SourceEnum = Field(description="후보 레시피를 가져온 검색 소스")
    # 식약처 RCP_SEQ, Spoonacular id처럼 원본을 다시 찾을 수 있는 키 (Tavily는 고유 ID가 없으므로 None, url로 대체)
    # RCP_SEQ는 문자열("137"), Spoonacular id는 숫자(73420)라서 하나로 맞추기 위해 str로 저장
    source_id: str | None = Field(default=None, description="원본 데이터의 고유 ID (식약처 RCP_SEQ, Spoonacular id)")
