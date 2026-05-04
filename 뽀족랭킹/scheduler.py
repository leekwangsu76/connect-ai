"""
뽀족랭킹 자동 스케줄러 (scheduler.py)
매일 정해진 시간에 자동으로 데이터 수집·분석·발행을 실행합니다.
"""
import schedule
import time
import subprocess
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pipeline'))

from pipeline.crawler import collect_places
from pipeline.processor import generate_comparison


# ─────────────────────────────────────
# 매일 실행할 작업 목록
# 여기에 원하는 작업을 추가/수정하세요
# ─────────────────────────────────────
DAILY_TASKS = [
    # {"category": "분야", "area": "지역", "places": ["장소1", "장소2", ...]}
    # 장소를 비워두면 자동으로 TOP 5 검색 (추후 업데이트)
    {"category": "카페", "area": "성수동", "places": ["어니언 성수", "대림창고", "할아버지공장"]},
    # 필요한 작업 추가:
    # {"category": "맛집", "area": "홍대", "places": []},
    # {"category": "장례식장", "area": "서울", "places": []},
]

# ─────────────────────────────────────
# 자동 실행 시간 설정 (24시간 형식)
# ─────────────────────────────────────
COLLECT_TIME = "09:00"   # 매일 오전 9시 데이터 수집
ANALYZE_TIME = "09:30"   # 매일 오전 9시 30분 AI 분석
SYNC_TIME    = "10:00"   # 매일 오전 10시 GitHub 동기화


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    # 로그 파일에도 저장
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.txt"), "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


def run_daily_collect():
    """매일 자동 데이터 수집 실행"""
    log("=" * 40)
    log("자동 수집 시작")
    for task in DAILY_TASKS:
        try:
            log(f"수집 중: {task['area']} {task['category']}")
            collect_places(task["places"], area=task["area"], category=task["category"])
            log(f"수집 완료: {task['area']} {task['category']}")
        except Exception as e:
            log(f"오류: {task['area']} {task['category']} - {e}")
    log("자동 수집 완료")


def run_daily_analyze():
    """매일 자동 AI 분석 실행"""
    log("=" * 40)
    log("자동 분석 시작")
    for task in DAILY_TASKS:
        try:
            log(f"분석 중: {task['area']} {task['category']}")
            generate_comparison(task["category"], task["area"])
            log(f"분석 완료: {task['area']} {task['category']}")
        except Exception as e:
            log(f"오류: {task['area']} {task['category']} - {e}")
    log("자동 분석 완료")


def run_github_sync():
    """매일 GitHub 자동 동기화"""
    log("=" * 40)
    log("GitHub 동기화 시작")
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.run(["git", "add", "."], cwd=base, check=True)
        subprocess.run(["git", "commit", "-m", f"자동 수집: {datetime.now().strftime('%Y-%m-%d')}"], cwd=base)
        subprocess.run(["git", "push"], cwd=base, check=True)
        log("GitHub 동기화 완료")
    except Exception as e:
        log(f"GitHub 동기화 오류: {e}")


def start_scheduler():
    """스케줄러 시작"""
    log("=" * 40)
    log("뽀족랭킹 자동 스케줄러 시작")
    log(f"  수집: 매일 {COLLECT_TIME}")
    log(f"  분석: 매일 {ANALYZE_TIME}")
    log(f"  동기화: 매일 {SYNC_TIME}")
    log("=" * 40)

    # 스케줄 등록
    schedule.every().day.at(COLLECT_TIME).do(run_daily_collect)
    schedule.every().day.at(ANALYZE_TIME).do(run_daily_analyze)
    schedule.every().day.at(SYNC_TIME).do(run_github_sync)

    # 시작하자마자 한번 실행 옵션 (테스트용 주석 해제)
    # run_daily_collect()
    # run_daily_analyze()

    log("대기 중... (Ctrl+C로 종료)")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크


if __name__ == "__main__":
    start_scheduler()
