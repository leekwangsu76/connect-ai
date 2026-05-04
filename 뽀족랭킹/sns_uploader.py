"""
뽀족랭킹 SNS 자동 업로드 (sns_uploader.py)
수집·분석된 데이터를 인스타그램, 쓰레드, 페이스북에 자동 발행합니다.

사용 전 준비사항:
  1. 인스타그램 비즈니스 계정 전환
  2. Meta 개발자 계정 → API 키 발급
  3. config.py에 API 키 입력
"""
import os
import sys
import json
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pipeline'))

from pipeline.config import DATA_DIR

# ─────────────────────────────────────
# SNS API 키 설정 (config.py에서 관리)
# 준비되면 config.py에 추가하세요
# ─────────────────────────────────────
try:
    from pipeline.config import (
        META_ACCESS_TOKEN,   # Meta Graph API 토큰
        INSTAGRAM_ACCOUNT_ID,  # 인스타그램 비즈니스 계정 ID
        FACEBOOK_PAGE_ID       # 페이스북 페이지 ID
    )
    META_READY = True
except ImportError:
    META_READY = False


def generate_caption(comparison_text, category, area, model="gemma4:e4b"):
    """Gemma 4로 인스타 캡션 + 해시태그 생성"""
    from pipeline.config import OLLAMA_URL
    import urllib.request

    prompt = f"""당신은 SNS 마케터입니다.
아래는 {area} {category} 비교 분석 자료입니다.

{comparison_text[:1000]}

위 자료를 기반으로 인스타그램용 캡션을 작성하세요:
- 첫줄: 눈길을 끄는 제목 (이모지 포함)
- 본문: 핵심 정보 3~5줄 (실제 데이터 기반)
- 마지막: 해시태그 20개 (한국어)
- 전체 300자 이내
- 절대 지어내지 말고 위 자료에서만 추출하세요"""

    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3}
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        res = urllib.request.urlopen(req, timeout=120)
        return json.loads(res.read().decode("utf-8")).get("response", "")
    except Exception as e:
        print(f"캡션 생성 실패: {e}")
        return ""


def post_to_instagram(caption, image_url=None):
    """인스타그램에 게시물 업로드"""
    if not META_READY:
        print("⚠️ Meta API 키가 설정되지 않았습니다. config.py에 키를 추가하세요.")
        return False

    try:
        # 1단계: 미디어 컨테이너 생성
        container_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media"
        payload = {
            "caption": caption,
            "access_token": META_ACCESS_TOKEN
        }
        if image_url:
            payload["image_url"] = image_url

        res = requests.post(container_url, data=payload)
        container_id = res.json().get("id")

        if not container_id:
            print(f"❌ 컨테이너 생성 실패: {res.json()}")
            return False

        # 2단계: 게시물 발행
        publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        res = requests.post(publish_url, data={
            "creation_id": container_id,
            "access_token": META_ACCESS_TOKEN
        })

        if res.json().get("id"):
            print(f"✅ 인스타그램 업로드 완료!")
            return True
        else:
            print(f"❌ 업로드 실패: {res.json()}")
            return False

    except Exception as e:
        print(f"❌ 인스타그램 오류: {e}")
        return False


def post_to_facebook(caption):
    """페이스북 페이지에 게시물 업로드"""
    if not META_READY:
        print("⚠️ Meta API 키가 설정되지 않았습니다.")
        return False

    try:
        url = f"https://graph.facebook.com/v18.0/{FACEBOOK_PAGE_ID}/feed"
        res = requests.post(url, data={
            "message": caption,
            "access_token": META_ACCESS_TOKEN
        })
        if res.json().get("id"):
            print("✅ 페이스북 업로드 완료!")
            return True
        return False
    except Exception as e:
        print(f"❌ 페이스북 오류: {e}")
        return False


def upload_comparison(category, area):
    """
    비교표 파일을 읽어서 SNS에 자동 업로드합니다.
    """
    print(f"\n📤 SNS 업로드 시작: {area} {category}")

    # 비교표 파일 읽기
    comparison_path = os.path.join(DATA_DIR, category, area, "_비교표.md")
    if not os.path.exists(comparison_path):
        print(f"❌ 비교표 없음: {comparison_path}")
        return

    with open(comparison_path, "r", encoding="utf-8") as f:
        comparison_text = f.read()

    # 캡션 생성
    print("🤖 캡션 생성 중...")
    caption = generate_caption(comparison_text, category, area)
    if not caption:
        print("❌ 캡션 생성 실패")
        return

    print(f"\n생성된 캡션:\n{'-'*30}\n{caption}\n{'-'*30}")

    # 캡션 저장 (SNS용 소스 파일)
    output_dir = os.path.join(DATA_DIR, category, area)
    caption_path = os.path.join(output_dir, "_SNS캡션.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(f"=== {area} {category} SNS 캡션 ===\n")
        f.write(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(caption)
    print(f"💾 캡션 저장: {caption_path}")

    # SNS 업로드 (API 키 준비 후 활성화)
    if META_READY:
        post_to_instagram(caption)
        post_to_facebook(caption)
    else:
        print("\n⚠️ API 키 미설정 → 캡션 파일만 저장됨")
        print("   인스타 비즈니스 계정 준비 후 config.py에 키 추가하면 자동 업로드됩니다.")


if __name__ == "__main__":
    upload_comparison("카페", "성수동")
