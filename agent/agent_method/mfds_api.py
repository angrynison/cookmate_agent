import os
import httpx
from dotenv import load_dotenv

load_dotenv()
MFDS_API_KEY = os.getenv("MFDS_API_KEY")

# Ministry of Food and Drug Safety (MFDS)
def search_recipes_mfds(pantries: list[str]) -> list[dict]:
    """
    MFDS(식약처) API를 사용하여 레시피를 검색
    """

    # 1. 재료 리스트를 쉼표(,)로 연결 (예: "돼지고기,김치")
    pantry_str = "&".join(pantries)
    
    # 2. 식약처 API 명세에 맞게 URL 경로 완성 
    # 기본구조: /api/{인증키}/{서비스명}/{요청타입}/{시작}/{종료}/추가변수=값
    url = f"http://openapi.foodsafetykorea.go.kr/api/{MFDS_API_KEY}/COOKRCP01/json/1/3/RCP_PARTS_DTLS={pantry_str}"

    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()

    if response.status_code == 200:
        data = response.json()
        return data.get("COOKRCP01", {}).get("row", [])
    
    return []