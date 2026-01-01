from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import random
import numpy as np
from datetime import datetime, timedelta
from garminconnect import Garmin
import pandas as pd
from db_manager import init_db, save_activities, get_all_activities, get_activity_stream, save_activity_stream
import traceback
import math

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
        # 直近x件取得
        activities = client.get_activities(0, 10000)
        parsed_data = []
        for activity in activities:
            # running (ロード), treadmill_running (トレッドミル), trail_running (トレイル), track_running (トラック)
            # これら全てを「ランニング」として認める。
            current_type = activity['activityType']['typeKey']
            if current_type not in ['running', 'treadmill_running', 'trail_running', 'track_running', 'virtual_run']:
                continue
            dist_m = activity.get('distance', 0)
            duration_s = activity.get('duration', 1)
            avg_hr = activity.get('averageHR', 0)
            if dist_m == 0 or avg_hr == 0: continue
            dist_km = dist_m / 1000
            duration_min = duration_s / 60
            pace_min_km = duration_min / dist_km if dist_km > 0 else 0
            speed_m_min = dist_m / duration_min if duration_min > 0 else 0
            efficiency = speed_m_min / avg_hr if avg_hr > 0 else 0
            pitch = activity.get('averageRunningCadenceInStepsPerMinute', 0.0)
            avg_stride = activity.get('avgStrideLength', 0.0)
            fastest_1km_min = round(activity.get('fastestSplit_1000') / 60, 2) if activity.get('fastestSplit_1000') else None
            fastest_1mile_min = round(activity.get('fastestSplit_1609') / 60, 2) if activity.get('fastestSplit_1609') else None
            fastest_5km_min = round(activity.get('fastestSplit_5000') / 60, 2) if activity.get('fastestSplit_5000') else None
            fastest_10km_min = round(activity.get('fastestSplit_10000') / 60, 2) if activity.get('fastestSplit_10000') else None

            parsed_data.append({
                "activity_id": activity['activityId'],
                "runner_id": activity['ownerId'],
                "runner_name": activity['ownerFullName'],
                "activity_name": activity['activityName'],
                "description": activity.get('description', ""),
                "activity_type": activity['activityType']['typeKey'],
                "trainning_effect_label": activity.get('trainingEffectLabel', ""),
                "aerobic_te_message": activity.get('aerobicTrainingEffectMessage', ""),
                "anaerobic_te_message": activity.get('anaerobicTrainingEffectMessage', ""),
                "date": activity['startTimeLocal'],
                "distance_km": round(dist_km, 2),
                "duration_min": round(duration_min, 2),
                "avg_hr": round(avg_hr, 1),
                "pace_min_km": round(pace_min_km, 2),
                "avg_pitch_spm": round(pitch, 1),
                "avg_stride_cm": round(avg_stride, 2),
                "calories": activity['calories'],
                "speed_m_min": round(speed_m_min, 1),
                "fastestSplit_1000": fastest_1km_min,
                "fastestSplit_1609": fastest_1mile_min,
                "fastestSplit_5000": fastest_5km_min,
                "fastestSplit_10000": fastest_10km_min,
                "elevation_gain": round(activity.get('elevationGain'), 1) if activity.get('elevationGain') else 0.0,
                "elevation_loss": round(activity.get('elevationLoss'), 1) if activity.get('elevationLoss') else 0.0,
                "hr_z1": round(activity['hrTimeInZone_1'] / 60, 2) if activity.get('hrTimeInZone_1') else 0.0,
                "hr_z2": round(activity['hrTimeInZone_2'] / 60, 2) if activity.get('hrTimeInZone_2') else 0.0,
                "hr_z3": round(activity['hrTimeInZone_3'] / 60, 2) if activity.get('hrTimeInZone_3') else 0.0,
                "hr_z4": round(activity['hrTimeInZone_4'] / 60, 2) if activity.get('hrTimeInZone_4') else 0.0,
                "hr_z5": round(activity['hrTimeInZone_5'] / 60, 2) if activity.get('hrTimeInZone_5') else 0.0,
                "aerobic_te": round(activity['aerobicTrainingEffect'], 2) if activity.get('aerobicTrainingEffect') else 0.0,
                "anaerobic_te": round(activity['anaerobicTrainingEffect'], 2) if activity.get('anaerobicTrainingEffect') else 0.0,
                "efficiency_score": round(efficiency, 2)
            })
        return save_activities(parsed_data)
    except Exception as e:
        # 修正後: 犯人の顔写真を撮る！
        print("========== GARMIN SYNC ERROR TRACEBACK ==========")
        print(f"Error Message: '{e}'")  # ここが空だったやつ
        print(f"Error Type: {type(e)}")  # エラーの種類（TypeErrorなのかHTTPErrorなのか）
        traceback.print_exc()  # どこで起きたか全行表示
        print("=================================================")
        return 0

# --- 詳細データ取得 & 整形 ---
# --- 詳細データ取得 & 整形 (修正版: エラー回避ロジック強化) ---
def fetch_garmin_details(activity_id):
    client = get_garmin_client()
    if not client:
        raise Exception("Garmin credentials missing or login failed.")

    print(f"Fetching details for {activity_id}...")
    try:
        details = client.get_activity_details(activity_id)
    except Exception as e:
        print(f"API Error: {e}")
        raise Exception(f"Failed to fetch from Garmin API: {e}")

    # 1. 設計図（metricDescriptors）を取得
    # これが「配列の何番目が何のデータか」を教えてくれる
    descriptors = details.get('metricDescriptors', [])
    metrics_data = details.get('activityDetailMetrics', [])

    if not descriptors or not metrics_data:
        return []

    # 2. インデックスとキーの対応表を作る
    # 例: { 4: 'directHeartRate', 5: 'directCadence' ... }
    key_map = {}
    for desc in descriptors:
        if 'metricsIndex' in desc and 'key' in desc:
            key_map[desc['metricsIndex']] = desc['key']



    processed_streams = []
    start_time = None
    print(descriptors)
    print(metrics_data[0:5])

    for point in metrics_data:
        # 配列データ（数字の羅列）を取得
        values = point.get('metrics', [])
        if not values or not isinstance(values, list):
            continue

        # 3. 数字の羅列を、意味のある辞書に変換する
        # 例: [120, 180] -> {'directHeartRate': 120, 'directCadence': 180}
        current_metrics = {}
        for index, val in enumerate(values):
            if index in key_map:
                key_name = key_map[index]
                current_metrics[key_name] = val

        # 必要なデータを取り出す
        # タイムスタンプの取得（配列の中にある場合と、外にある場合の両方に対応）
        timestamp = point.get('timestamp')  # 外側にある場合
        if not timestamp:
            # 配列の中にある場合 ('directTimestamp' などのキーを探す)
            # ※お前のデータを見ると、非常に大きな数字(1767048404000.0)がタイムスタンプだ
            # key_mapで 'time' や 'timestamp' 系のキーがマッピングされているはず
            for k, v in current_metrics.items():
                if 'timestamp' in k.lower() or 'time' in k.lower():
                    # ミリ秒の場合は秒になおす
                    if v > 1000000000000:
                        timestamp = v / 1000.0
                    else:
                        timestamp = v
                    break

        if not timestamp:
            continue

        if start_time is None: start_time = timestamp
        elapsed_min = (timestamp - start_time) / 60.0

        hr = current_metrics.get('directHeartRate')
        elapsed_duration = current_metrics.get('sumElapsedDuration')
        sum_distance = current_metrics.get('sumDistance')
        speed_mps = current_metrics.get('directSpeed')
        vertical_speed = current_metrics.get('directVerticalSpeed')
        cadence = current_metrics.get('directRunCadence') or current_metrics.get('directCadence')
        stride = current_metrics.get('directStrideLength')  # cm
        if stride is None and speed_mps and cadence and cadence > 0:
            cadence = cadence * 2
            # (m/s * 60) / spm = m/step.  それを * 100 して cm に変換
            stride = (speed_mps * 60 / cadence) * 100

        # Pace計算
        pace_min_km = None
        if speed_mps is not None and isinstance(speed_mps, (int, float)) and speed_mps > 0.1:
            try:
                pace = 16.666 / speed_mps
                if 2.0 < pace < 20.0:
                    pace_min_km = round(pace, 2)
            except:
                pace_min_km = None

        processed_streams.append({
            "time_min": round(elapsed_min, 2),
            "hr": hr if hr is not None else None,
            "elapsed_duration": elapsed_duration,
            "sum_distance": sum_distance,
            "pace_min_km": pace_min_km,
            "cadence": cadence if cadence is not None else None,
            "vertical_speed": vertical_speed,
            "stride_m": round(stride / 100, 2) if stride is not None else None
        })

    print(f"Processed {len(processed_streams)} points for activity {activity_id}")
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
    # データがなければモック
    generate_mock_if_empty()

    df = get_all_activities()

    if df.empty:
        return {"stats": {}, "activities": [], "feedback": "データがないぞ。"}

    # ★ ラモス流・完全浄化プロセス
    # DataFrameを辞書リストに変換してから、1つずつ検査して NaN を None に変える
    # これなら Pandas のバージョンや挙動に左右されず確実に消せる
    activities_list = df.to_dict(orient="records")
    clean_activities = []

    for act in activities_list:
        clean_act = {}
        for k, v in act.items():
            # float型の NaN (Not a Number) かどうか判定
            if isinstance(v, float) and (math.isnan(v) or v == float('inf')):
                clean_act[k] = None
            else:
                clean_act[k] = v
        clean_activities.append(clean_act)

    # 統計値の計算 (ここも安全に)
    avg_eff = df['efficiency_score'].mean()
    recent_df = df.tail(7)
    recent_eff = recent_df['efficiency_score'].mean()
    avg_pace = recent_df['pace_min_km'].mean()

    # 統計値が NaN なら 0.0 に置換
    stats = {
        "weekly_volume_km": round(recent_df['distance_km'].sum(), 1),
        "avg_efficiency": round(avg_eff if not math.isnan(avg_eff) else 0.0, 2),
        "recent_efficiency": round(recent_eff if not math.isnan(recent_eff) else 0.0, 2)
    }

    feedback = "分析完了。"
    if stats["recent_efficiency"] > stats["avg_efficiency"]:
        feedback = "良い傾向だ。効率が上がっている。"

    return {
        "stats": stats,
        "feedback": feedback,
        "activities": clean_activities  # 浄化済みデータを返す
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
