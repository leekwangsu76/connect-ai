"""
뽀족랭킹 네이버 플레이스 크롤러 (place_crawler.py)
가격, 영업시간, 평점 등 상세 데이터를 수집합니다.
"""
import requests
from bs4 import BeautifulSoup
import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET


def search_place_url(place_name, area=""):
    """네이버 지역검색 API로 플레이스 URL을 찾습니다."""
    import urllib.request, urllib.parse, json
    query = f"{area} {place_name}".strip()
    params = urllib.parse.urlencode({"query": query, "display": 1})
    url = f"https://openapi.naver.com/v1/search/local.json?{params}"
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
    req.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)
    try:
        res = urllib.request.urlopen(req)
        data = json.loads(res.read().decode("utf-8"))
        if data.get("items"):
            return data["items"][0].get("link", "")
    except:
        pass
    return ""


def crawl_place_detail(place_name, area=""):
    """
    네이버 플레이스에서 상세 정보를 크롤링합니다.
    가격, 영업시간, 평점 등을 수집합니다.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9"
    }

    detail = {
        "name": place_name,
        "rating": "미확인",
        "review_count": "미확인",
        "hours": "미확인",
        "price_range": "미확인",
        "menu_items": [],
        "place_url": ""
    }

    try:
        # 네이버 검색으로 플레이스 찾기
        search_url = f"https://search.naver.com/search.naver?query={requests.utils.quote(f'{area} {place_name}')}&where=place"
        res = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        # 평점 추출
        rating_el = soup.select_one(".h69bs span.orXYY") or soup.select_one("[class*='rating']")
        if rating_el:
            detail["rating"] = rating_el.get_text(strip=True)

        # 영업시간 추출
        hours_el = soup.select_one("[class*='businessHours']") or soup.select_one("[class*='hours']")
        if hours_el:
            detail["hours"] = hours_el.get_text(strip=True)[:100]

        # 가격대 추출
        price_el = soup.select_one("[class*='price']") or soup.select_one("[class*='cost']")
        if price_el:
            detail["price_range"] = price_el.get_text(strip=True)[:100]

        # 메뉴 추출 (리뷰 텍스트에서 가격 패턴 찾기)
        price_pattern = re.compile(r'[\w\s]+\s+[\d,]+원')
        text_blocks = soup.find_all(string=price_pattern)
        for block in text_blocks[:5]:
            matches = price_pattern.findall(str(block))
            detail["menu_items"].extend(matches[:3])

    except Exception as e:
        detail["error"] = str(e)

    return detail


if __name__ == "__main__":
    result = crawl_place_detail("어니언 성수", "성수동")
    print(result)
