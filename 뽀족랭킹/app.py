"""
뽀족랭킹 웹 대시보드 서버 (app.py)
브라우저에서 버튼 클릭으로 수집·분석을 실행합니다.
"""
from flask import Flask, render_template_string, jsonify, request
import threading, os, sys, json, glob
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pipeline'))

from pipeline.crawler import collect_places
from pipeline.processor import generate_comparison
from pipeline.config import DATA_DIR, OLLAMA_MODEL, PROCESS_MODE, REVIEW_MODE

app = Flask(__name__)

# 작업 상태 저장
task_status = {"running": False, "log": [], "last_result": ""}


def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    task_status["log"].append(f"[{timestamp}] {msg}")
    print(msg)


HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>뽀족랭킹 데이터 파이프라인</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; min-height: 100vh; }

  header { background: linear-gradient(135deg, #1a1f2e, #252b3b); padding: 20px 30px; border-bottom: 1px solid #2a3040; }
  header h1 { font-size: 1.6rem; color: #7eb8ff; letter-spacing: -0.5px; }
  header p { font-size: 0.85rem; color: #666; margin-top: 4px; }

  .container { max-width: 900px; margin: 30px auto; padding: 0 20px; }

  .card { background: #1a1f2e; border: 1px solid #2a3040; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
  .card h2 { font-size: 1rem; color: #7eb8ff; margin-bottom: 16px; }

  .form-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; }
  .form-group { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 150px; }
  label { font-size: 0.8rem; color: #888; }
  input, select { background: #0f1117; border: 1px solid #2a3040; color: #e0e0e0; padding: 10px 12px; border-radius: 8px; font-size: 0.9rem; }
  input:focus, select:focus { outline: none; border-color: #7eb8ff; }

  .btn { padding: 10px 24px; border-radius: 8px; border: none; cursor: pointer; font-size: 0.9rem; font-weight: 600; transition: all 0.2s; }
  .btn-primary { background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; }
  .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(59,130,246,0.4); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
  .btn-success { background: linear-gradient(135deg, #10b981, #059669); color: white; }
  .btn-success:hover { transform: translateY(-1px); }

  .status-bar { display: flex; gap: 16px; flex-wrap: wrap; }
  .status-item { background: #0f1117; border: 1px solid #2a3040; border-radius: 8px; padding: 10px 16px; font-size: 0.8rem; }
  .status-item span { color: #7eb8ff; font-weight: 600; }

  .log-box { background: #0a0d14; border: 1px solid #2a3040; border-radius: 8px; padding: 16px; height: 200px; overflow-y: auto; font-family: monospace; font-size: 0.8rem; line-height: 1.6; }
  .log-box p { color: #7eb8ff; }
  .log-empty { color: #444; }

  .results-grid { display: grid; gap: 12px; }
  .result-card { background: #0f1117; border: 1px solid #2a3040; border-radius: 8px; padding: 16px; display: flex; justify-content: space-between; align-items: center; }
  .result-card:hover { border-color: #3b82f6; }
  .result-info h3 { font-size: 0.95rem; color: #e0e0e0; }
  .result-info p { font-size: 0.78rem; color: #666; margin-top: 3px; }
  .badge { font-size: 0.7rem; background: #1e3a5f; color: #7eb8ff; padding: 3px 8px; border-radius: 20px; }

  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #3b82f6; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .progress { height: 3px; background: #2a3040; border-radius: 3px; margin-top: 8px; }
  .progress-bar { height: 100%; background: linear-gradient(90deg, #3b82f6, #7eb8ff); border-radius: 3px; transition: width 0.5s; }
</style>
</head>
<body>
<header>
  <h1>🎯 뽀족랭킹 데이터 파이프라인</h1>
  <p>실제 데이터 수집 · AI 분석 · 비교표 생성</p>
</header>

<div class="container">

  <!-- 현재 설정 -->
  <div class="card">
    <h2>⚙️ 현재 설정</h2>
    <div class="status-bar">
      <div class="status-item">모델: <span id="model">{{ model }}</span></div>
      <div class="status-item">처리방식: <span id="mode">{{ process_mode }}</span></div>
      <div class="status-item">리뷰방식: <span id="review">{{ review_mode }}</span></div>
    </div>
  </div>

  <!-- 수집 실행 -->
  <div class="card">
    <h2>🔍 데이터 수집 + 분석 실행</h2>
    <div class="form-row">
      <div class="form-group">
        <label>분야</label>
        <select id="category">
          <option value="카페">카페</option>
          <option value="맛집">맛집</option>
          <option value="장례식장">장례식장</option>
          <option value="건설">건설</option>
          <option value="인테리어">인테리어</option>
          <option value="병원">병원</option>
          <option value="숙소">숙소</option>
        </select>
      </div>
      <div class="form-group">
        <label>지역</label>
        <input id="area" type="text" placeholder="예: 성수동" value="성수동">
      </div>
      <div class="form-group">
        <label>장소명 (쉼표로 구분)</label>
        <input id="places" type="text" placeholder="예: 어니언 성수, 대림창고" value="어니언 성수, 대림창고, 할아버지공장">
      </div>
      <button class="btn btn-primary" id="runBtn" onclick="runPipeline()">▶ 실행</button>
    </div>
    <div class="progress" style="margin-top:16px">
      <div class="progress-bar" id="progressBar" style="width:0%"></div>
    </div>
  </div>

  <!-- 로그 -->
  <div class="card">
    <h2>📋 실행 로그 <span id="spinner" style="display:none"><span class="spinner"></span></span></h2>
    <div class="log-box" id="logBox">
      <span class="log-empty">실행하면 여기에 진행 상황이 표시됩니다.</span>
    </div>
  </div>

  <!-- 결과 파일 목록 -->
  <div class="card">
    <h2>📁 수집된 데이터</h2>
    <div class="results-grid" id="resultsGrid">
      <p style="color:#444;font-size:0.85rem">수집된 데이터가 없습니다.</p>
    </div>
    <button class="btn btn-success" style="margin-top:16px" onclick="loadResults()">🔄 새로고침</button>
  </div>

</div>

<script>
let pollInterval;

function runPipeline() {
  const category = document.getElementById('category').value;
  const area = document.getElementById('area').value.trim();
  const placesRaw = document.getElementById('places').value.trim();
  const places = placesRaw.split(',').map(p => p.trim()).filter(p => p);

  if (!area || places.length === 0) {
    alert('지역과 장소명을 입력하세요.');
    return;
  }

  document.getElementById('runBtn').disabled = true;
  document.getElementById('spinner').style.display = 'inline';
  document.getElementById('logBox').innerHTML = '';
  document.getElementById('progressBar').style.width = '10%';

  fetch('/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({category, area, places})
  });

  pollInterval = setInterval(pollStatus, 2000);
}

function pollStatus() {
  fetch('/status').then(r => r.json()).then(data => {
    const box = document.getElementById('logBox');
    box.innerHTML = data.log.map(l => `<p>${l}</p>`).join('') || '<span class="log-empty">대기 중...</span>';
    box.scrollTop = box.scrollHeight;

    if (!data.running) {
      clearInterval(pollInterval);
      document.getElementById('runBtn').disabled = false;
      document.getElementById('spinner').style.display = 'none';
      document.getElementById('progressBar').style.width = '100%';
      setTimeout(() => document.getElementById('progressBar').style.width = '0%', 2000);
      loadResults();
    } else {
      const pct = Math.min(90, 10 + data.log.length * 5);
      document.getElementById('progressBar').style.width = pct + '%';
    }
  });
}

function loadResults() {
  fetch('/results').then(r => r.json()).then(data => {
    const grid = document.getElementById('resultsGrid');
    if (data.length === 0) {
      grid.innerHTML = '<p style="color:#444;font-size:0.85rem">수집된 데이터가 없습니다.</p>';
      return;
    }
    grid.innerHTML = data.map(f => `
      <div class="result-card">
        <div class="result-info">
          <h3>${f.name}</h3>
          <p>${f.path} · ${f.modified}</p>
        </div>
        <span class="badge">${f.type}</span>
      </div>
    `).join('');
  });
}

// 초기 로드
loadResults();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML, model=OLLAMA_MODEL,
                                   process_mode=PROCESS_MODE,
                                   review_mode=REVIEW_MODE)


@app.route("/run", methods=["POST"])
def run():
    if task_status["running"]:
        return jsonify({"error": "이미 실행 중"}), 400

    data = request.json
    category = data.get("category", "카페")
    area = data.get("area", "")
    places = data.get("places", [])

    def task():
        task_status["running"] = True
        task_status["log"] = []
        try:
            log(f"▶ 수집 시작: {area} {category} {len(places)}곳")
            collect_places(places, area=area, category=category)
            log(f"✅ 수집 완료!")
            log(f"🧠 AI 분석 시작...")
            generate_comparison(category, area)
            log(f"✅ 비교표 생성 완료!")
        except Exception as e:
            log(f"❌ 오류: {e}")
        finally:
            task_status["running"] = False

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/status")
def status():
    return jsonify({"running": task_status["running"], "log": task_status["log"]})


@app.route("/results")
def results():
    files = []
    for md in glob.glob(os.path.join(DATA_DIR, "**", "*.md"), recursive=True):
        name = os.path.basename(md)
        rel = os.path.relpath(md, DATA_DIR)
        mtime = datetime.fromtimestamp(os.path.getmtime(md)).strftime("%Y-%m-%d %H:%M")
        ftype = "비교표" if name.startswith("_") else "장소데이터"
        files.append({"name": name, "path": rel, "modified": mtime, "type": ftype})
    files.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify(files[:30])


if __name__ == "__main__":
    print("\n" + "="*50)
    print("🎯 뽀족랭킹 대시보드 시작")
    print("   브라우저에서 http://localhost:5000 접속")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
