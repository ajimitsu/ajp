from fastapi import FastAPI, BackgroundTasks, HTTPException
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
