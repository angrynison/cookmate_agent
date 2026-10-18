"""
식약처 원본(data/mfds_raw.json)의 재료 문자열을 LLM으로 정규화해 data/mfds_recipes.json 으로 저장하는 일회성 배치 스크립트
(서버가 실행하는 코드가 아니라, 데이터를 준비할 때 돌리는 도구. download_mfds.py로 원본을 먼저 받아 둔다)

실행: 프로젝트 루트에서
    python -m scripts.normalize_mfds            # 전체
    python -m scripts.normalize_mfds --limit 3  # 앞에서 3건만 시험 (비용·시간 확인용)

중간에 멈춰도 이어서 실행할 수 있다
    - 성공한 레시피는 한 건씩 즉시 data/mfds_recipes.partial.jsonl 에 추가 저장한다
    - 다시 실행하면 그 파일에 있는 RCP_SEQ는 건너뛰고, 실패했던 레시피만 다시 시도한다
    - 처음부터 다시 돌리고 싶으면 partial 파일을 지우고 실행한다
"""
import argparse
import json
import time
from collections import Counter
from pathlib import Path

from agent.agent_dto import FormattedRecipe, SourceEnum
from agent.agent_method.mfds.mfds_api import extract_steps
from scripts.normalize_mfds_llm import (
    normalize_ingredients_with_llm,
    validate_ingredients,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_PATH = DATA_DIR / "mfds_raw.json"                      # 원본 레시피 JSON 
PARTIAL_PATH = DATA_DIR / "mfds_recipes.partial.json"      # 중간 저장: 성공한 레시피를 한 줄씩 추가 (실패한 레시피는 다시 시도 가능)
OUTPUT_PATH = DATA_DIR / "mfds_recipes.json"                # 최종 저장: 성공한 레시피 전체
FAILURES_PATH = DATA_DIR / "mfds_normalize_failures.json"   # 실패한 데이터 저장

PROGRESS_EVERY = 20        # 몇 건마다 진행 상황을 출력할지
EARLY_STOP_CALLS = 5       # 처음 N건이 전부 실패하면 중단 (키 누락·코드 버그로 비용만 쓰는 것 방지)


class IngredientValidationError(ValueError):
    """LLM 결과가 원문과 맞지 않을 때 (실패 기록에서 LLM 호출 오류와 구분하기 위한 예외)"""

# mfds_raw.json 읽기
def load_raw_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_done_recipes(path: Path) -> dict[str, FormattedRecipe]:
    """
    이전 실행에서 이미 성공한 레시피를 읽는다 → {RCP_SEQ: 레시피}
    파일이 없으면 빈 dict. 강제 종료로 마지막 줄이 반쯤 쓰였으면 그 줄만 버린다(다시 처리됨) -> validate_json으로 검사
    """
    done: dict[str, FormattedRecipe] = {}
    # 중간 저장.json에 존재하지 않는다면 첫 실행이니 비어있는 done return
    if not path.exists():
        return done

    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():    # 빈 문자열 건너뛰기 strip() -> 앞뒤 공백,줄바꿈 지우기
                continue
            try:
                recipe = FormattedRecipe.model_validate_json(line) # JSON 파싱검사, 모델 검증 (문자열이 JSON 문법에 맞나?, 필드와 타입이 올바른가)
            except ValueError:
                continue
            done[recipe.source_id] = recipe
    return done


def ensure_newline(path: Path) -> None:
    """
    강제 종료로 마지막 줄이 줄바꿈 없이 반쯤 쓰였으면 줄바꿈을 하나 붙인다
    예 {"title":"방울토마토 소박이", "sou{"title":"부추전",...}\n
    """
    if not path.exists() or path.stat().st_size == 0:
        return
    with open(path, "rb") as f:
        f.seek(-1, 2)              # 파일 끝에서 1바이트 앞으로 이동
        last_byte = f.read(1)
    if last_byte != b"\n":
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n")


def check_data(row: dict) -> str | None:
    """
    LLM을 부르기 전에 하는 검사
    """
    if not row.get("RCP_SEQ"):
        return "RCP_SEQ 없음"
    if not (row.get("RCP_NM") or "").strip():
        return "제목 없음"
    if not (row.get("RCP_PARTS_DTLS") or "").strip():
        return "재료 문자열 없음"
    if not extract_steps(row):
        return "조리 단계 없음"
    return None


def normalize_row(row: dict) -> FormattedRecipe:
    """
    레시피 1건 정규화. 실패하면 예외를 던진다 (기록과 계속 진행은 호출하는 쪽이 정한다)
    """
    title = row["RCP_NM"].strip()
    dtls = row["RCP_PARTS_DTLS"]

    normalized = normalize_ingredients_with_llm(title, dtls)

    # 원문과 대조 검증. 실패하면 IngredientValidationError
    errors = validate_ingredients(dtls, normalized)
    if errors:
        raise IngredientValidationError(" / ".join(errors[:5]))

    # 규칙으로 뽑은 제목·단계·팁·ID + LLM이 뽑은 재료 → FormattedRecipe 조립
    return FormattedRecipe(
        title=title,
        ingredients=normalized.ingredients,   
        steps=extract_steps(row),
        tip=(row.get("RCP_NA_TIP") or "").strip() or None,   
        source=SourceEnum.MFDS,
        source_id=row["RCP_SEQ"],
    )


def normalize_all_rows(rows: list[dict], done: dict[str, FormattedRecipe]) -> tuple[list[dict], Counter]:
    """
    row를 한 건씩 정규화한다. 성공하면 즉시 partial 파일에 한 줄 추가하고 done에 넣는다
    반환: (이번 실행의 실패 목록, 건너뛴 이유별 개수)
    """
    failures: list[dict] = []       # 이번 실행에서 실패한 레시피 목록 (원본 dict + 오류 메시지)
    skipped: Counter = Counter()    # 이번 실행에서 건너뛴 레시피 개수 (이유별), Counter는 없는 키를 0으로 초기화해주는 dict -> 처음보는 이유도 오류x
    called = 0                      # LLM 호출 횟수
    started = time.perf_counter()   # 시작 시각 기록

    # "a"(append) 모드: 이전 실행 결과를 지우지 않고 뒤에 이어 쓴다
    ensure_newline(PARTIAL_PATH)
    with open(PARTIAL_PATH, "a", encoding="utf-8") as partial:
        for row in rows:
            source_id = row.get("RCP_SEQ")
            if source_id in done:
                skipped["이미 처리됨"] += 1
                continue

            reason = check_data(row)
            if reason:
                skipped[reason] += 1
                continue

            called += 1
            try:
                recipe = normalize_row(row)
            except Exception as e:   # 한 건의 실패(네트워크·요청 한도·검증)가 전체를 멈추지 않게
                failures.append({
                    "source_id": source_id,
                    "title": row.get("RCP_NM"),
                    "error_type": type(e).__name__,
                    "error": str(e),
                })
                # 처음 N건이 모두 실패하면 중단 (키 누락·코드 버그로 비용만 쓰는 것 방지)
                if called >= EARLY_STOP_CALLS and len(failures) == called:
                    print(f"처음 {called}건이 모두 실패해서 중단합니다. 마지막 오류: {failures[-1]}")
                    break
                continue

            # 성공 즉시 저장 → 800번째에서 멈춰도 앞의 결과는 남는다
            partial.write(recipe.model_dump_json() + "\n") # DTO -> JSON 문자열로 변환 후 한 줄씩 저장
            partial.flush() #  파이썬 버퍼 -> 운영체제로 넘김
            done[source_id] = recipe

            if called % PROGRESS_EVERY == 0:
                elapsed = time.perf_counter() - started
                print(f"  {called}건 호출 / 실패 {len(failures)}건 / {elapsed:.0f}초 (건당 {elapsed / called:.1f}초)")

    elapsed = time.perf_counter() - started
    if called:
        print(f"LLM 호출 {called}건, {elapsed:.1f}초 (건당 {elapsed / called:.1f}초)")
    return failures, skipped


def save_recipes(recipes: list[FormattedRecipe], path: Path) -> None:
    """정규화된 레시피 DTO 목록을 JSON 파일로 저장한다 (DTO → dict 변환이 필요해서 model_dump)"""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [recipe.model_dump(mode="json") for recipe in recipes]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_failures(failures: list[dict], path: Path) -> None:
    """이번 실행에서 실패한 레시피 목록 (원본 dict라 변환 없이 저장)"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(failures, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="식약처 레시피 재료를 LLM으로 정규화")
    parser.add_argument("--limit", type=int, default=None, help="앞에서 N건만 처리 (시험용)")
    args = parser.parse_args()

    
    all_rows = load_raw_rows(RAW_PATH)      # 원본 레시피 mdfs_raw.json 읽기
    target_rows = all_rows[: args.limit] if args.limit else all_rows # limit 옵션이 있으면 앞에서 N건만 처리, 없으면 전체
    done = load_done_recipes(PARTIAL_PATH)  # 이전 실행에서 마지막으로 성공한 레시피 싹 읽기 dict 형식 (RCP_SEQ → FormattedRecipe)
    print(f"원본 {len(all_rows)}건 중 {len(target_rows)}건 대상, 이전에 완료된 레시피 {len(done)}건")

    failures, skipped = normalize_all_rows(target_rows, done)

    # 최종 파일은 원본 순서대로 다시 정렬해서 쓴다 (partial은 실행·재시도 순서라 섞여 있을 수 있음)
    ordered = [done[row["RCP_SEQ"]] for row in all_rows if row.get("RCP_SEQ") in done]
    save_recipes(ordered, OUTPUT_PATH)
    save_failures(failures, FAILURES_PATH)

    print(f"저장 완료: {OUTPUT_PATH} ({len(ordered)}건)")
    print(f"건너뜀: {dict(skipped)}")
    print(f"실패 {len(failures)}건 → {FAILURES_PATH} (다시 실행하면 실패한 것만 재시도)")


if __name__ == "__main__":
    main()