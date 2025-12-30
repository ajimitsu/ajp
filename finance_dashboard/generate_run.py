import zipfile
import os

files = {
    # ==============================
    # Docker / Config (変更なし)
    # ==============================
    "docker-compose.yml": """version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - sqlite_data:/app/data
    env_file:
      - .env
    environment:
      - USE_REAL_GARMIN=True
      - DB_PATH=/app/data/running_log.db
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
    stdin_open: true
    tty: true
    depends_on:
      - backend
volumes:
  sqlite_data:
""",
    ".env": """# Garmin Connect Credentials
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password
# Setting
USE_REAL_GARMIN=True
""",

    # ==============================
    # Backend (大幅アップデート)
    # ==============================
    "backend/Dockerfile": """FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
""",
    "backend/requirements.txt": """fastapi
uvicorn
pandas
garminconnect
pydantic
numpy
""",

    # DB Manager: 詳細データを格納するテーブルを追加
    "backend/db_manager.py": """import sqlite3
import pandas as pd
import os
import json

DB_PATH = os.getenv("DB_PATH", "running_log.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # サマリー用テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            activity_id INTEGER PRIMARY KEY,
            date TEXT,
            distance_km REAL,
            duration_min REAL,
            avg_hr REAL,
            pace_min_km REAL,
            speed_m_min REAL,
            efficiency_score REAL
        )
    ''')
    # 詳細ストリームデータ用テーブル（巨大なJSONとして保存）
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_streams (
            activity_id INTEGER PRIMARY KEY,
            streams_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- サマリー系 ---
def save_activities(activities_list):
    if not activities_list: return 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    count = 0
    for a in activities_list:
        try:
            c.execute('''
                INSERT OR IGNORE INTO activities 
                (activity_id, date, distance_km, duration_min, avg_hr, pace_min_km, speed_m_min, efficiency_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (a['activity_id'], a['date'], a['distance_km'], a['duration_min'], a['avg_hr'], a['pace_min_km'], a['speed_m_min'], a['efficiency_score']))
            if c.rowcount > 0: count += 1
        except Exception as e: print(f"Error saving activity: {e}")
    conn.commit()
    conn.close()
    return count

def get_all_activities():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM activities ORDER BY date ASC", conn)
    conn.close()
    return df

# --- 詳細ストリーム系 ---
def get_activity_stream(activity_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT streams_json FROM activity_streams WHERE activity_id = ?", (activity_id,))
    result = c.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

def save_activity_stream(activity_id, streams_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # JSON文字列として保存
    c.execute("INSERT OR REPLACE INTO activity_streams (activity_id, streams_json) VALUES (?, ?)",
              (activity_id, json.dumps(streams_data)))
    conn.commit()
    conn.close()
""",

    # Main: 詳細データ取得ロジックを追加
    "backend/main.py": """from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import random
import numpy as np
from datetime import datetime, timedelta
from garminconnect import Garmin
import pandas as pd
from db_manager import init_db, save_activities, get_all_activities, get_activity_stream, save_activity_stream

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# --- Garmin Client Helper ---
def get_garmin_client():
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    if not email or "example.com" in email: return None
    try:
        client = Garmin(email, password)
        client.login()
        return client
    except Exception as e:
        print(f"Garmin Login Error: {e}")
        return None

# --- サマリー同期 ---
def fetch_and_sync_garmin():
    client = get_garmin_client()
    if not client: return 0
    try:
        # 直近20件取得
        activities = client.get_activities(0, 20) 
        parsed_data = []
        for activity in activities:
            if activity['activityType']['typeKey'] != 'running': continue
            dist_m = activity.get('distance', 0)
            duration_s = activity.get('duration', 1)
            avg_hr = activity.get('averageHR', 0)
            if dist_m == 0 or avg_hr == 0: continue
            dist_km = dist_m / 1000
            duration_min = duration_s / 60
            pace_min_km = duration_min / dist_km if dist_km > 0 else 0
            speed_m_min = dist_m / duration_min if duration_min > 0 else 0
            efficiency = speed_m_min / avg_hr if avg_hr > 0 else 0

            parsed_data.append({
                "activity_id": activity['activityId'],
                "date": activity['startTimeLocal'].split(' ')[0],
                "distance_km": round(dist_km, 2),
                "duration_min": round(duration_min, 2),
                "avg_hr": round(avg_hr, 1),
                "pace_min_km": round(pace_min_km, 2),
                "speed_m_min": round(speed_m_min, 1),
                "efficiency_score": round(efficiency, 2)
            })
        return save_activities(parsed_data)
    except Exception as e:
        print(f"Garmin Sync Error: {e}")
        return 0

# --- 詳細データ取得 & 整形 ---
def fetch_garmin_details(activity_id):
    client = get_garmin_client()
    if not client: raise Exception("Garmin credentials missing")

    # Garminから詳細データを取得 (これが重い処理)
    details = client.get_activity_details(activity_id)

    # 必要なメトリクスを抽出して時系列データに整形
    metrics = details.get('activityDetailMetrics', [])
    processed_streams = []

    start_time = None

    for point in metrics:
        metrics_map = {m['key']: m['value'] for m in point.get('metrics', [])}

        timestamp = point.get('timestamp')
        if start_time is None: start_time = timestamp

        # 経過時間 (分)
        elapsed_min = (timestamp - start_time) / 60.0

        # 必要なデータを取り出す（存在しない場合はNone）
        hr = metrics_map.get('directHeartRate')
        speed_mps = metrics_map.get('directSpeed') # m/s
        cadence = metrics_map.get('directCadence') # spm
        stride = metrics_map.get('directStrideLength') # meters

        # Pace (min/km) に変換: (1000 / 60) / speed_mps
        pace_min_km = None
        if speed_mps and speed_mps > 0.1: # 止まっている時を除外
             pace_min_km = 16.666 / speed_mps
             # 異常値を除外 (例: 20分/kmより遅い、2分/kmより速い)
             if pace_min_km > 20 or pace_min_km < 2: pace_min_km = None

        processed_streams.append({
            "time_min": round(elapsed_min, 2),
            "hr": hr,
            "pace_min_km": round(pace_min_km, 2) if pace_min_km else None,
            "cadence": cadence,
            "stride_m": round(stride/100, 2) if stride else None # cmからmへ変換
        })

    # データ量削減のため、nullが多い行や重要でない行を間引く処理をここに入れても良い
    return processed_streams

# --- モック生成 (省略) ---
def generate_mock_if_empty(): pass # v2と同じなので省略。実データ推奨。

# --- API Endpoints ---
@app.get("/api/sync")
def trigger_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(fetch_and_sync_garmin)
    return {"message": "Sync started in background"}

@app.get("/api/dashboard")
def get_dashboard_data():
    df = get_all_activities()
    if df.empty: return {"stats": {}, "activities": [], "feedback": "Syncボタンを押してデータを取得しろ。"}
    recent_df = df.tail(7)
    avg_eff = df['efficiency_score'].mean()
    recent_eff = recent_df['efficiency_score'].mean()

    feedback = "分析中..."
    if recent_eff > avg_eff: feedback = "良い傾向だ。効率が上がっている。"
    else: feedback = "注意：効率低下の兆候あり。"

    return {
        "stats": {
            "weekly_volume_km": round(recent_df['distance_km'].sum(), 1),
            "avg_efficiency": round(avg_eff, 1),
            "recent_efficiency": round(recent_eff, 1)
        },
        "feedback": feedback,
        "activities": df.to_dict(orient="records")
    }

# ★新設: 詳細データ取得API
@app.get("/api/activity/{activity_id}")
def get_activity_details_api(activity_id: int):
    # 1. まずDBを確認
    streams = get_activity_stream(activity_id)
    if streams:
        print(f"Serving activity {activity_id} from DB.")
        return {"activity_id": activity_id, "streams": streams}

    # 2. DBになければGarminから取得
    if os.getenv("USE_REAL_GARMIN") == "True":
        print(f"Fetching activity {activity_id} from Garmin API...")
        try:
            streams = fetch_garmin_details(activity_id)
            # DBに保存
            save_activity_stream(activity_id, streams)
            return {"activity_id": activity_id, "streams": streams}
        except Exception as e:
            print(f"Error fetching details: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=404, detail="Data not found and Garmin sync disabled.")
""",

    # ==============================
    # Frontend (React)
    # ==============================
    "frontend/Dockerfile": """FROM node:18-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
""",
    "frontend/package.json": """{
  "name": "ramos-frontend-v3",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "axios": "^1.6.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "recharts": "^2.10.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  },
  "browserslist": {
    "production": [ ">0.2%", "not dead", "not op_mini all" ],
    "development": [ "last 1 chrome version" ]
  }
}
""",
    "frontend/public/index.html": """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8" /><meta name="viewport" content="width=device-width" /><title>Ramos V3</title></head>
<body><div id="root"></div></body></html>
""",
    "frontend/src/index.js": """import React from 'react'; import ReactDOM from 'react-dom/client'; import './index.css'; import App from './App';
const root = ReactDOM.createRoot(document.getElementById('root')); root.render(<React.StrictMode><App /></React.StrictMode>);""",
    "frontend/src/index.css": """body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background-color: #f4f4f9; }""",

    # CSS: モーダルウィンドウ用のスタイルを追加
    "frontend/src/App.css": """.dashboard-container { max-width: 1200px; margin: 0 auto; padding: 20px; color: #333; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;}
.sync-btn { background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }
.sync-btn:hover { background-color: #2980b9; }
.stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.card, .chart-card, .feedback-section { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.stat-value { font-size: 2em; font-weight: bold; margin: 5px 0; }
.diff.good { color: green; } .diff.bad { color: red; }
.feedback-section { background-color: #2c3e50; color: white; border-left: 5px solid #e74c3c; margin-bottom:20px;}
.chart-card { margin-bottom: 20px; }
/* モーダル */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); display: flex; justify-content: center; align-items: center; z-index: 1000; }
.modal-content { background: white; padding: 20px; border-radius: 10px; width: 90%; max-width: 1000px; max-height: 90vh; overflow-y: auto; position: relative; }
.close-btn { position: absolute; top: 10px; right: 15px; font-size: 24px; cursor: pointer; border:none; background:none;}
.detail-chart-row { height: 200px; margin-bottom: 10px; }
.chart-title { margin: 5px 0; font-size: 1em; font-weight:bold; color: #555; }
""",

    # App.js: メイン画面。グラフクリックでモーダルを開く処理を追加。
    "frontend/src/App.js": """import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import ActivityDetail from './ActivityDetail';
import './App.css';

function App() {
  const [data, setData] = useState(null);
  const [syncing, setSyncing] = useState(false);
  // 選択されたアクティビティIDを管理
  const [selectedActivityId, setSelectedActivityId] = useState(null);

  const fetchData = () => {
    axios.get('http://localhost:8000/api/dashboard')
      .then(response => setData(response.data))
      .catch(error => console.error("Error:", error));
  };

  useEffect(() => { fetchData(); }, []);

  const handleSync = () => {
    setSyncing(true);
    axios.get('http://localhost:8000/api/sync').then(() => {
        alert("同期開始。しばらくしてリロードしろ。");
        setTimeout(() => { fetchData(); setSyncing(false); }, 5000);
      });
  };

  // グラフの点をクリックした時の処理
  const handleChartClick = (point) => {
    if (point && point.activePayload) {
      const activityId = point.activePayload[0].payload.activity_id;
      setSelectedActivityId(activityId);
    }
  };

  if (!data) return <div style={{padding:'20px'}}>Loading Dashboard...</div>;

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1>🏃 Ramos Analytics v3 (Deep Dive)</h1>
        <button className="sync-btn" onClick={handleSync} disabled={syncing}>
          {syncing ? "Syncing..." : "🔄 Sync Garmin"}
        </button>
      </header>

      {data.feedback && (
        <div className="feedback-section">
           <p style={{margin:0, fontWeight:'bold'}}>📢 Ramos Feedback: "{data.feedback}"</p>
        </div>
      )}

      <div className="charts-container">
        <div className="chart-card">
          <h3>Efficiency vs Pace Trend (Click points for details!)</h3>
          <p style={{fontSize:'0.9em'}}>点をクリックすると詳細分析画面が開くぞ。</p>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.activities} onClick={handleChartClick} style={{cursor:'pointer'}}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis yAxisId="left" domain={['auto', 'auto']} label={{ value: 'Efficiency', angle: -90, position: 'insideLeft' }}/>
              <YAxis yAxisId="right" orientation="right" domain={['auto', 'auto']} reversed={true} unit=" min/km" label={{ value: 'Pace (min/km)', angle: 90, position: 'insideRight' }}/>
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="efficiency_score" stroke="#8884d8" strokeWidth={3} name="Efficiency" dot={{ r: 5 }} activeDot={{ r: 8 }} />
              <Line yAxisId="right" type="monotone" dataKey="pace_min_km" stroke="#82ca9d" name="Pace (min/km)" dot={{ r: 5 }} activeDot={{ r: 8 }}/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 詳細モーダル表示 */}
      {selectedActivityId && (
        <ActivityDetail 
          activityId={selectedActivityId} 
          onClose={() => setSelectedActivityId(null)} 
        />
      )}
    </div>
  );
}

export default App;
""",

    # ★新設: ActivityDetail.js (詳細分析用モーダルコンポーネント)
    # ここが「pyplotみたいに」を実現するキモだ。
    "frontend/src/ActivityDetail.js": """import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function ActivityDetail({ activityId, onClose }) {
  const [streams, setStreams] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    // 詳細データ取得APIを叩く
    axios.get(`http://localhost:8000/api/activity/${activityId}`)
      .then(response => {
        setStreams(response.data.streams);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error fetching details:", err);
        setError("データの取得に失敗した。Garmin接続を確認しろ。");
        setLoading(false);
      });
  }, [activityId]);

  // ツールチップのカスタマイズ（複数グラフで同期表示させるためシンプルに）
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ background: 'white', padding: '5px', border: '1px solid #ccc' }}>
          <p style={{margin:0}}>{`Time: ${label} min`}</p>
          {payload.map((p, index) => (
            <p key={index} style={{margin:0, color: p.color}}>{`${p.name}: ${p.value} ${p.unit || ''}`}</p>
          ))}
        </div>
      );
    }
    return null;
  };

  // 共通のチャート設定 (syncIdが重要！)
  const commonChartProps = {
    data: streams,
    syncId: "activityDetailSync", // これで全てのグラフのX軸が同期する
    margin: { top: 5, right: 30, left: 20, bottom: 5 }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>&times;</button>
        <h2>Activity Analysis (ID: {activityId})</h2>

        {loading && <div>Loading detailed data from Garmin/DB... 解析中...</div>}
        {error && <div style={{color:'red'}}>{error}</div>}

        {streams && !loading && (
          <div>
            {/* 1. ペースグラフ */}
            <div className="chart-title">Pace (min/km) - 低いほど速い</div>
            <div className="detail-chart-row">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart {...commonChartProps}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time_min" type="number" domain={['dataMin', 'dataMax']} label={{ value: 'Time (min)', position: 'insideBottom', offset: -5 }}/>
                  {/* ペースは反転させた方が直感的 */}
                  <YAxis domain={['auto', 'auto']} reversed={true}/>
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="pace_min_km" stroke="#82ca9d" dot={false} name="Pace" unit="min/km" strokeWidth={2}/>
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* 2. 心拍数グラフ */}
            <div className="chart-title">Heart Rate (bpm)</div>
            <div className="detail-chart-row">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart {...commonChartProps}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time_min" hide={true}/> {/* 中間のX軸は隠す */}
                  <YAxis domain={['auto', 'auto']} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="hr" stroke="#ff7300" dot={false} name="HR" unit="bpm" strokeWidth={2}/>
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* 3. ピッチ (Cadence) グラフ */}
            <div className="chart-title">Cadence (spm)</div>
            <div className="detail-chart-row">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart {...commonChartProps}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time_min" hide={true}/>
                  <YAxis domain={['auto', 'auto']} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="cadence" stroke="#8884d8" dot={false} name="Cadence" unit="spm" />
                </LineChart>
              </ResponsiveContainer>
            </div>

             {/* 4. ストライド (Stride Length) グラフ */}
            <div className="chart-title">Stride Length (m)</div>
            <div className="detail-chart-row">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart {...commonChartProps}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time_min" hide={true}/>
                  <YAxis domain={['auto', 'auto']} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="stride_m" stroke="#ffc658" dot={false} name="Stride" unit="m" />
                </LineChart>
              </ResponsiveContainer>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}

export default ActivityDetail;
"""
}

zip_filename = "ramos-dashboard-v3.zip"
with zipfile.ZipFile(zip_filename, 'w') as zipf:
    for file_path, content in files.items():
        zipf.writestr(file_path, content)
print(f"'{zip_filename}' 生成完了。ミクロ分析の準備は整った。")