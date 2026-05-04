# 뽀족랭킹 데이터 파이프라인

실제 데이터 수집 → AI 분석 → SNS 자동 발행 시스템

---

## 데스크탑 세팅 (30분)

### 1. 필수 프로그램 설치
- [Python](https://python.org) 다운로드 설치
- [Ollama](https://ollama.ai) 다운로드 설치
- [Git](https://git-scm.com) 다운로드 설치
- [Tailscale](https://tailscale.com) 다운로드 설치 → hnk9927@gmail.com 로그인

### 2. 코드 받기
```bash
git clone https://github.com/[저장소주소]/connect-ai.git
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. AI 모델 다운로드 (20분)
```bash
ollama pull gemma4:e4b
```

### 5. 실행
```bash
# 웹 대시보드
python run.py

# 자동 스케줄러
python scheduler.py
```

브라우저에서 **http://localhost:5000** 접속

---

## 파일 구조

```
뽀족랭킹/
├── run.py              ← 웹 대시보드 실행
├── scheduler.py        ← 자동 스케줄 실행
├── sns_uploader.py     ← SNS 자동 업로드
├── app.py              ← 웹 서버
├── requirements.txt    ← 패키지 목록
├── pipeline/
│   ├── config.py       ← 모든 설정 (여기서만 수정)
│   ├── crawler.py      ← 네이버 API 수집
│   ├── processor.py    ← Gemma 4 분석
│   └── place_crawler.py← 네이버 플레이스 상세
└── data/               ← 수집된 데이터 저장
    ├── 카페/
    ├── 맛집/
    └── 장례식장/
```

---

## SNS 자동 업로드 설정 (준비 후)

`pipeline/config.py` 하단에 추가:
```python
META_ACCESS_TOKEN    = "여기에_메타_토큰"
INSTAGRAM_ACCOUNT_ID = "여기에_계정ID"
FACEBOOK_PAGE_ID     = "여기에_페이지ID"
```

---

## 작업 일정 변경

`scheduler.py`의 `DAILY_TASKS` 수정:
```python
DAILY_TASKS = [
    {"category": "카페", "area": "성수동", "places": [...]},
    {"category": "맛집", "area": "홍대",   "places": [...]},
]
```
