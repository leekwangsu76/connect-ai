"""
뽀족랭킹 데이터 정제기 (processor.py)
config.py 옵션에 따라 다양한 방식으로 Gemma 4 분석을 수행합니다.
"""
import urllib.request
import json
import os
import sys
import glob
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TEMPERATURE,
    DATA_DIR, PROCESS_MODE, REVIEW_MODE, REVIEW_SUMMARY_LENGTH
)


def call_gemma(prompt):
    """로컬 Ollama의 Gemma 4를 호출합니다."""
    data = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": OLLAMA_TEMPERATURE,
            "num_predict": 2000
        }
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        response = urllib.request.urlopen(request, timeout=300)
        result = json.loads(response.read().decode("utf-8"))
        return result.get("response", "")
    except Exception as e:
        print(f"  ⚠️ Gemma 호출 실패: {e}")
        return None


def prepare_review_text(content, place_name):
    """
    REVIEW_MODE에 따라 리뷰 텍스트를 준비합니다.
    config.py의 REVIEW_MODE 옵션에 따라 동작이 달라집니다.
    """
    if REVIEW_MODE == "summary":
        # summary 모드: 리뷰 제목 + 앞부분만 잘라서 전달 (가볍고 빠름)
        lines = content.split('\n')
        review_lines = []
        in_review = False
        collected = 0

        for line in lines:
            if '블로그 리뷰' in line:
                in_review = True
            if in_review and (line.startswith('### 리뷰') or line.startswith('>')):
                review_lines.append(line.strip())
                collected += len(line)
                if collected >= REVIEW_SUMMARY_LENGTH:
                    break

        return f"[{place_name}]\n" + '\n'.join(review_lines)

    else:
        # full 모드: 파일 전체 내용 전달 (정보 풍부하지만 무거움)
        return f"[{place_name}]\n{content}"


def extract_basic_info(content, place_name):
    """파일에서 기본 정보(주소, 카테고리 등)만 추출합니다."""
    basic = []
    for line in content.split('\n'):
        if any(k in line for k in ['상호명', '카테고리', '도로명', '전화번호', '링크', '리뷰']):
            clean = re.sub(r'[#*|]', '', line).strip()
            if clean:
                basic.append(clean)
    return f"[{place_name} 기본정보]\n" + '\n'.join(basic[:10])


def analyze_one_place(place_name, content):
    """
    PROCESS_MODE = "one_by_one" 일 때:
    장소 1곳씩 따로 분석합니다. (정확도 높음)
    """
    review_text = prepare_review_text(content, place_name)
    basic_text = extract_basic_info(content, place_name)

    prompt = f"""당신은 뽀족랭킹 데이터 분석가입니다.
아래는 '{place_name}'의 실제 수집 데이터입니다.

절대 규칙:
- 아래 데이터에 있는 내용만 사용하세요
- 없는 정보는 반드시 "미확인"으로 적으세요
- 절대 지어내지 마세요

=== 기본 정보 ===
{basic_text}

=== 리뷰 내용 ===
{review_text}

위 데이터만 보고 아래 항목을 작성하세요:

**장소명:** {place_name}
**주소:** (위 데이터에서 찾기)
**카테고리:** (위 데이터에서 찾기)
**리뷰에서 언급된 메뉴/가격:** (위 데이터에서 찾기, 없으면 미확인)
**리뷰 키워드 5개:** (자주 나오는 단어)
**한줄 요약:** (데이터 기반으로 한 문장)
"""
    print(f"  🤖 {place_name} 분석 중...")
    return call_gemma(prompt)


def analyze_all_at_once(files_data):
    """
    PROCESS_MODE = "all_at_once" 일 때:
    전체 장소를 한번에 분석합니다. (빠르지만 정확도 낮을 수 있음)
    """
    combined = ""
    for fd in files_data:
        combined += "\n\n" + prepare_review_text(fd['content'], fd['name'])
        combined += "\n" + extract_basic_info(fd['content'], fd['name'])

    prompt = f"""당신은 뽀족랭킹 데이터 분석가입니다.
아래는 {len(files_data)}개 장소의 실제 수집 데이터입니다.

절대 규칙:
- 아래 데이터에 있는 내용만 사용하세요
- 없는 정보는 "미확인"으로 적으세요
- 절대 지어내지 마세요

{combined}

위 데이터를 기반으로 비교표를 작성하세요:

| 항목 | {' | '.join([fd['name'] for fd in files_data])} |
|---|{'---|' * len(files_data)}
| 주소 | (각 장소 주소) |
| 카테고리 | (각 장소 카테고리) |
| 언급 메뉴/가격 | (리뷰에서 찾기, 없으면 미확인) |
| 리뷰 키워드 | (각 5개) |
| 한줄 요약 | (각 1문장) |
"""
    print(f"  🤖 전체 {len(files_data)}곳 한번에 분석 중...")
    return call_gemma(prompt)


def read_place_files(category, area):
    """특정 분야/지역의 수집된 데이터 파일들을 읽어옵니다."""
    search_dir = os.path.join(DATA_DIR, category, area)
    if not os.path.exists(search_dir):
        print(f"❌ 폴더 없음: {search_dir}")
        return []

    files_data = []
    for filepath in glob.glob(os.path.join(search_dir, "*.md")):
        filename = os.path.basename(filepath)
        if filename.startswith("_"):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        name = filename.replace(".md", "").replace("_", " ")
        files_data.append({"name": name, "filepath": filepath, "content": content})
        print(f"  📄 읽음: {filename}")

    return files_data


def generate_comparison(category, area):
    """수집된 데이터를 Gemma 4로 분석하여 비교표를 생성합니다."""
    print(f"\n{'='*50}")
    print(f"🧠 뽀족 비교표 생성 시작")
    print(f"   분야: {category} | 지역: {area}")
    print(f"   모델: {OLLAMA_MODEL}")
    print(f"   처리방식: {PROCESS_MODE} | 리뷰방식: {REVIEW_MODE}({REVIEW_SUMMARY_LENGTH}자)")
    print(f"{'='*50}")

    files_data = read_place_files(category, area)
    if not files_data:
        print("❌ 분석할 데이터가 없습니다.")
        return None

    # ─── 처리 방식 분기 ───
    if PROCESS_MODE == "one_by_one":
        # 장소 1개씩 분석 후 합치기 (정확도 높음)
        results = []
        for fd in files_data:
            result = analyze_one_place(fd['name'], fd['content'])
            if result:
                results.append(result)
        final_content = "\n\n---\n\n".join(results)

    else:
        # 전체 한번에 분석 (빠름)
        final_content = analyze_all_at_once(files_data)

    if not final_content:
        print("❌ Gemma 4 분석 실패")
        return None

    # 저장
    save_dir = os.path.join(DATA_DIR, category, area)
    output_path = os.path.join(save_dir, "_비교표.md")

    output = f"""# {area} {category} 뽀족 비교표

- **분석일:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
- **분석 대상:** {', '.join([fd['name'] for fd in files_data])}
- **모델:** {OLLAMA_MODEL}
- **처리방식:** {PROCESS_MODE} / 리뷰방식: {REVIEW_MODE}({REVIEW_SUMMARY_LENGTH}자)
- **데이터 출처:** 네이버 검색 API + 블로그 리뷰

---

{final_content}

---
> ⚠️ 수집된 실제 데이터만을 기반으로 생성. 미확인 항목은 추가 조사 필요.
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n✅ 비교표 저장 완료: {output_path}")
    print(f"{'='*50}\n")
    return output_path


if __name__ == "__main__":
    generate_comparison("카페", "성수동")
