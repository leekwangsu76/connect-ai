"""
뽀족랭킹 데이터 수집기 (crawler.py)
네이버 검색 API로 실제 장소 데이터를 수집합니다.
"""
import urllib.request
import urllib.parse
import json
import os
import sys
from datetime import datetime

# 설정 불러오기
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, DATA_DIR


def search_naver(query, display=10, api_type="local"):
    """
    네이버 검색 API를 호출하여 실제 데이터를 가져옵니다.
    api_type: "local" (지역검색), "blog" (블로그), "webkr" (웹)
    """
    base_url = f"https://openapi.naver.com/v1/search/{api_type}.json"
    sort_value = "comment" if api_type == "local" else "sim"
    params = urllib.parse.urlencode({
        "query": query,
        "display": display,
        "sort": sort_value
    })
    url = f"{base_url}?{params}"

    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
    request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)

    try:
        response = urllib.request.urlopen(request)
        result = json.loads(response.read().decode("utf-8"))
        return result
    except Exception as e:
        print(f"❌ 검색 실패: {e}")
        return None


def clean_html(text):
    """HTML 태그 제거"""
    import re
    return re.sub(r"<[^>]+>", "", text)


def collect_place_data(place_name, area=""):
    """
    특정 장소의 데이터를 수집합니다.
    """
    query = f"{area} {place_name}" if area else place_name
    print(f"\n🔍 검색 중: {query}")

    # 1. 지역 검색 (가격, 주소, 전화번호 등)
    local_result = search_naver(query, display=5, api_type="local")
    
    # 2. 블로그 검색 (리뷰, 분위기, 후기)
    blog_result = search_naver(f"{place_name} 후기 리뷰", display=10, api_type="blog")

    place_data = {
        "name": place_name,
        "area": area,
        "collected_at": datetime.now().isoformat(),
        "source": "네이버 검색 API",
        "local_info": [],
        "blog_reviews": []
    }

    # 지역 정보 파싱
    if local_result and "items" in local_result:
        for item in local_result["items"]:
            place_data["local_info"].append({
                "title": clean_html(item.get("title", "")),
                "category": item.get("category", ""),
                "address": item.get("address", ""),
                "roadAddress": item.get("roadAddress", ""),
                "telephone": item.get("telephone", ""),
                "link": item.get("link", ""),
                "mapx": item.get("mapx", ""),
                "mapy": item.get("mapy", "")
            })
        print(f"  ✅ 지역 정보 {len(local_result['items'])}건 수집")

    # 블로그 리뷰 파싱
    if blog_result and "items" in blog_result:
        for item in blog_result["items"]:
            place_data["blog_reviews"].append({
                "title": clean_html(item.get("title", "")),
                "description": clean_html(item.get("description", "")),
                "link": item.get("link", ""),
                "postdate": item.get("postdate", "")
            })
        print(f"  ✅ 블로그 리뷰 {len(blog_result['items'])}건 수집")

    return place_data


def save_place_data(place_data, category="카페"):
    """
    수집된 데이터를 AI 최적화 구조로 저장합니다.
    - 고정된 섹션 구조 (AI가 항상 같은 위치에서 정보를 찾음)
    - 메뉴/가격은 표로 분리 (수치 명확화)
    - 키워드는 태그로 분리 (검색 최적화)
    - 출처/날짜 명시 (신뢰도 확보)
    """
    area = place_data["area"] or "기타"
    save_dir = os.path.join(DATA_DIR, category, area)
    os.makedirs(save_dir, exist_ok=True)

    safe_name = place_data["name"].replace(" ", "_")
    filepath = os.path.join(save_dir, f"{safe_name}.md")

    # 기본 정보 추출
    info = place_data["local_info"][0] if place_data["local_info"] else {}

    # 리뷰에서 가격 패턴 추출 (예: "앙버터 3,800원")
    import re
    price_pattern = re.compile(r'([가-힣a-zA-Z\s]{2,10})\s*([\d,]+)\s*원')
    extracted_prices = []
    for review in place_data["blog_reviews"]:
        matches = price_pattern.findall(review["description"])
        for menu, price in matches:
            menu = menu.strip()
            if len(menu) >= 2 and menu not in [m[0] for m in extracted_prices]:
                extracted_prices.append((menu, price + "원",
                    review["postdate"], review["link"]))

    # 리뷰에서 키워드 추출 (자주 등장하는 명사)
    all_text = " ".join([r["description"] for r in place_data["blog_reviews"]])
    keyword_candidates = re.findall(r'[가-힣]{2,5}', all_text)
    from collections import Counter
    stop_words = {"이번", "오늘", "우리", "그리고", "정말", "너무", "하지만", "있어", "있는",
                  "없는", "이런", "저런", "이곳", "여기", "거기", "이미", "더욱", "또한"}
    keyword_freq = Counter([w for w in keyword_candidates if w not in stop_words])
    top_keywords = [kw for kw, _ in keyword_freq.most_common(10)]

    # ── AI 최적화 MD 작성 ──
    collected_date = place_data["collected_at"][:10]  # YYYY-MM-DD만

    md_content = f"""# {place_data['name']}

## 메타데이터
| 항목 | 값 |
|---|---|
| **분류** | {category} |
| **지역** | {area} |
| **수집일** | {collected_date} |
| **데이터출처** | {place_data['source']} |
| **신뢰도** | 실제수집 (AI생성아님) |

---

## 기본 정보
| 항목 | 값 | 출처 |
|---|---|---|
| **상호명** | {info.get('title', '미확인')} | 네이버 지역검색 |
| **카테고리** | {info.get('category', '미확인')} | 네이버 지역검색 |
| **도로명 주소** | {info.get('roadAddress', '미확인')} | 네이버 지역검색 |
| **전화번호** | {info.get('telephone', '미확인') or '미확인'} | 네이버 지역검색 |
| **홈페이지** | {info.get('link', '미확인') or '미확인'} | 네이버 지역검색 |
| **영업시간** | 미확인 | 추가수집필요 |
| **주차** | 미확인 | 추가수집필요 |
| **평점** | 미확인 | 추가수집필요 |

---

## 메뉴 및 가격
*(리뷰에서 자동 추출 — 실제 가격과 다를 수 있으니 검증 필요)*

| 메뉴명 | 가격 | 확인날짜 | 출처 |
|---|---|---|---|
"""
    if extracted_prices:
        for menu, price, date, link in extracted_prices[:10]:
            md_content += f"| {menu} | {price} | {date} | [블로그]({link}) |\n"
    else:
        md_content += "| 미확인 | 미확인 | - | 추가수집필요 |\n"

    md_content += f"""
---

## 키워드 분석
*(리뷰 {len(place_data['blog_reviews'])}건에서 자동 추출)*

### 자주 등장한 단어
{" ".join([f"#{kw}" for kw in top_keywords]) if top_keywords else "#키워드없음"}

### 분위기 키워드
- 미확인 (리뷰 분석 후 수동 추가 권장)

### 추천 대상
- 미확인 (리뷰 분석 후 수동 추가 권장)

---

## 블로그 리뷰 원문
*(최신 {len(place_data['blog_reviews'])}건)*

"""
    for i, review in enumerate(place_data["blog_reviews"], 1):
        md_content += f"""### [{i}] {review['title']}
- **날짜:** {review['postdate']}
- **링크:** {review['link']}
- **요약:** {review['description'][:300]}

"""

    md_content += f"""---

## 연관 노드 (지식 그래프)
[[{category}]] [[{area}]] {" ".join([f"[[{kw}]]" for kw in top_keywords[:5]])}

---
> 수집일: {collected_date} | 출처: 네이버 검색 API | AI생성: 아니오
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"  💾 저장 완료: {filepath}")
    return filepath


def collect_places(places, area="", category="카페"):
    """
    여러 장소를 한번에 수집합니다.
    
    사용법:
        collect_places(["어니언 성수", "대림창고", "할아버지공장"], area="성수동", category="카페")
    """
    print(f"\n{'='*50}")
    print(f"🚀 뽀족랭킹 데이터 수집 시작")
    print(f"   지역: {area or '전체'} | 분류: {category}")
    print(f"   대상: {', '.join(places)}")
    print(f"{'='*50}")

    results = []
    for place in places:
        data = collect_place_data(place, area)
        filepath = save_place_data(data, category)
        results.append({"name": place, "filepath": filepath, "data": data})

    print(f"\n{'='*50}")
    print(f"✅ 수집 완료! {len(results)}곳 데이터 저장됨")
    print(f"📁 저장 위치: {os.path.join(DATA_DIR, category, area or '기타')}")
    print(f"{'='*50}\n")

    return results


if __name__ == "__main__":
    # 테스트: 성수동 카페 3곳 수집
    collect_places(
        ["어니언 성수", "대림창고", "할아버지공장"],
        area="성수동",
        category="카페"
    )
