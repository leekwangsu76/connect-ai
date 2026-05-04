"""
뽀족랭킹 통합 실행 파일 (run.py)
이 파일 하나만 실행하면 모든 기능이 시작됩니다.

사용법:
  python run.py              → 웹 대시보드 실행
  python run.py --collect    → 커맨드라인으로 직접 수집
"""
import sys
import os

def main():
    if "--collect" in sys.argv:
        # 커맨드라인 모드
        from pipeline.crawler import collect_places
        from pipeline.processor import generate_comparison

        category = sys.argv[sys.argv.index("--category") + 1] if "--category" in sys.argv else "카페"
        area = sys.argv[sys.argv.index("--area") + 1] if "--area" in sys.argv else "성수동"
        places_str = sys.argv[sys.argv.index("--places") + 1] if "--places" in sys.argv else ""
        places = [p.strip() for p in places_str.split(",") if p.strip()]

        if not places:
            print("오류: --places 옵션에 장소명을 입력하세요.")
            print("예: python run.py --collect --category 카페 --area 성수동 --places 어니언성수,대림창고")
            sys.exit(1)

        collect_places(places, area=area, category=category)
        generate_comparison(category, area)

    else:
        # 웹 대시보드 모드 (기본)
        os.environ["PYTHONIOENCODING"] = "utf-8"
        from app import app
        print("\n" + "="*50)
        print("🎯 뽀족랭킹 대시보드 시작!")
        print("   브라우저에서 http://localhost:5000 접속")
        print("="*50 + "\n")
        app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
