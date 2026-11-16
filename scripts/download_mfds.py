import json
from pathlib import Path
import httpx
from dotenv import load_dotenv
import os

# MFDS 최대 요청 개수가 1000개임
PAGE_SIZE = 1000

# 실행 위치와 상관없이 항상 "프로젝트 루트/data/mfds_recipes.json"에 저장
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "mfds_raw.json"

def fetch_mfds_rows(start: int, end: int) -> tuple[list[dict], int]:
    """
    MFDS API에서 start~end 범위의 레시피 row를 가져온다.
    반환값: (rows, total)
    """

    load_dotenv()
    MFDS_API_KEY = os.getenv("MFDS_API_KEY")
    if not MFDS_API_KEY:
        raise ValueError("MFDS_API_KEY 환경 변수가 설정되지 않았습니다.")

    url = "https://openapi.foodsafetykorea.go.kr/api/{}/COOKRCP01/json/{}/{}".format(
        MFDS_API_KEY, start, end
    )

    response = httpx.get(url)
    response.raise_for_status()

    data = response.json()
    rows = data["COOKRCP01"]["row"]
    total = int(data["COOKRCP01"]["total_count"])
    return rows, total



def download_all_rows() -> list[dict]:
    """
    전체 레시피 row를 PAGE_SIZE개(1000개가 최대)씩 나눠서 모두 받는다
    """
    # 총 레시피 개수 가져오기 (1156개)
    _, total = fetch_mfds_rows(1, 1)    

    all_rows: list[dict] = []
    for start in range(1, total + 1, PAGE_SIZE):
        # 마지막 구간은 total 넘지 않도록 제한
        end = min(start + PAGE_SIZE - 1, total)

        rows, _ = fetch_mfds_rows(start, end)
        # extend로 원소들을 이어 붙임
        all_rows.extend(rows)

    return all_rows

def save_all_rows(rows: list[dict], path: Path) -> None:
    """
    MFDS API 검색 결과 list를 JSON 파일로 저장한다.
    """
    path.parent.mkdir(parents=True, exist_ok=True)   
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)



def main() -> None:
    rows = download_all_rows()
    save_all_rows(rows,OUTPUT_PATH)


if __name__ == "__main__":
    main()
