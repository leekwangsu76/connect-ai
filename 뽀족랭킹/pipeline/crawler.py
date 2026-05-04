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
    수집된 데이터를 Markdown 파일로 저장합니다.
    """
    area = place_data["area"] or "기타"
    save_dir = os.path.join(DATA_DIR, category, area)
    os.makedirs(save_dir, exist_ok=True)

    # 파일명 생성 (특수문자 제거)
    safe_name = place_data["name"].replace(" ", "_")
    filepath = os.path.join(save_dir, f"{safe_name}.md")

    # Markdown 작성
    md_content = f"""# {place_data['name']}

- **분류:** {category}
- **지역:** {area}
- **수집일:** {place_data['collected_at']}
- **출처:** {place_data['source']}

---

## 📍 기본 정보 (네이버 지역 검색)

"""
    if place_data["local_info"]:
        info = place_data["local_info"][0]  # 첫 번째 결과 사용
        md_content += f"""| 항목 | 내용 |
|---|---|
| **상호명** | {info['title']} |
| **카테고리** | {info['category']} |
| **도로명 주소** | {info['roadAddress']} |
| **지번 주소** | {info['address']} |
| **전화번호** | {info['telephone'] or '미확인'} |
| **링크** | {info['link'] or '미확인'} |

### 기타 검색 결과
"""
        for i, item in enumerate(place_data["local_info"][1:], 2):
            md_content += f"- [{item['title']}]({item['link']}) - {item['category']}\n"
    else:
        md_content += "> 지역 검색 결과 없음\n"

    md_content += f"""

---

## 📝 블로그 리뷰 (최신 {len(place_data['blog_reviews'])}건)

"""
    if place_data["blog_reviews"]:
        for i, review in enumerate(place_data["blog_reviews"], 1):
            md_content += f"""### 리뷰 {i}: {review['title']}
> {review['description'][:200]}...

- 🔗 [원문 링크]({review['link']})
- 📅 {review['postdate']}

"""
    else:
        md_content += "> 블로그 리뷰 없음\n"

    md_content += f"""
---

## 🏷️ 태그

#{category} #{area} #{place_data['name'].replace(' ', '')}
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
