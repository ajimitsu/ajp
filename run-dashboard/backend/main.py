from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
import random
import numpy as np
from datetime import datetime, timedelta
from garminconnect import Garmin
import pandas as pd
from db_manager import init_db, save_activities, get_all_activities, get_activity_stream, save_activity_stream
import traceback
import math
import sqlite3
import shutil
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt

# --- 設定 ---
SECRET_KEY = "supersecretkey_change_me" # 本番では絶対に変えろ！
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# --- トレーニング設定 (Ramos Config) ---
USER_MAX_HR = 184   # 仮の値
USER_REST_HR = 51   # 仮の値
MALE_GENDER = True  # 男ならTrue, 女ならFalse (係数が違う)

# パスワードハッシュ化設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- データベース接続ヘルパー ---

# 1. マスターDB（会員名簿）への接続
def get_master_db():
    conn = sqlite3.connect("master_users.db")
    conn.row_factory = sqlite3.Row
    return conn

# 2. マスターテーブル作成（初回のみ実行）
def init_master_db():
    conn = get_master_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            hashed_password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_master_db()

# --- 認証ロジック ---

# パスワード検証
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# パスワードハッシュ化
def get_password_hash(password):
    return pwd_context.hash(password)

# トークン生成
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

class UserCreate(BaseModel):
    username: str
    password: str

@app.post("/register")
def register(user: UserCreate):
    conn = get_master_db()
    try:
        # 1. パスワードをハッシュ化してマスターDBに保存
        hashed_pw = get_password_hash(user.password)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (user.username, hashed_pw))
        conn.commit()
        user_id = cursor.lastrowid

        # 2. ★ここが重要！ そのユーザ専用のDBファイルを作成
        # テンプレート（空のDB）をコピーして、user_{id}.db を作る
        # テンプレートには 'activities' などのテーブル定義だけが入っている前提
        db_filename = f"user_data_{user_id}.db"
        init_db(db_filename)

        return {"msg": "User created successfully", "user_id": user_id}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already registered")
    finally:
        conn.close()


# --- ログイン用API ---

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_master_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (form_data.username,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    # トークンに user_id を埋め込む
    access_token = create_access_token(data={"sub": user['username'], "uid": user['id']})
    return {"access_token": access_token, "token_type": "bearer"}


# --- ★重要: 依存関係注入 (Dependency Injection) ---
async def get_current_user_id(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("uid")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


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


def calculate_trimp(duration_min, avg_hr):
    """
    TRIMP (Training Impulse) を計算する関数
    Banister's TRIMP formulaを使用
    """
    if not duration_min or not avg_hr or avg_hr < USER_REST_HR:
        return 0.0

    # 心拍予備能 (Heart Rate Reserve) の割合
    hrr_ratio = (avg_hr - USER_REST_HR) / (USER_MAX_HR - USER_REST_HR)

    # 男女で係数が違う
    b = 1.92 if MALE_GENDER else 1.67

    # 公式: 時間(分) x 強度 x 指数関数的重み付け
    trimp = duration_min * hrr_ratio * 0.64 * math.exp(b * hrr_ratio)

    return trimp

# --- サマリー同期 ---
def fetch_and_sync_garmin(user_id: int):
    print(f"--- [Background Task] Starting Sync for User ID: {user_id} ---")  # ログ追加

    db_file = f"user_data_{user_id}.db"
    if not os.path.exists(db_file):
        return []  # まだデータがない場合

    client = get_garmin_client()
    if not client:
        print("Garmin Client is None. Check env vars.")
        return 0
    try:
        # 直近x件取得
        # activities = client.get_activities(0, 10000)
        activities = client.get_activities(0, 3000)
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
            calculated_trimp = calculate_trimp(duration_min, avg_hr)

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
                "efficiency_score": round(efficiency, 2),
                "trimp": round(calculated_trimp, 1)
            })
        return save_activities(parsed_data, db_file)
    except Exception as e:
        print("========== GARMIN SYNC ERROR TRACEBACK ==========")
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
def trigger_sync(background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id)
                 ):
    background_tasks.add_task(fetch_and_sync_garmin, user_id)
    print(f"Sync request received for User ID: {user_id}")  # ログ確認用
    return {"message": "Sync started in background"}


@app.get("/api/dashboard")
def get_dashboard_data(user_id: int = Depends(get_current_user_id)):
    # データがなければモック
    generate_mock_if_empty()

    db_file = f"user_data_{user_id}.db"
    if not os.path.exists(db_file):
        return []  # まだデータがない場合

    df = get_all_activities(db_file)

    if df.empty:
        return {"stats": {}, "activities": [], "feedback": "データがないぞ。"}

    # 1. 日付でソートして、インデックスにする
    df['date_dt'] = pd.to_datetime(df['date'])
    df = df.sort_values('date_dt')

    df['day'] = df['date_dt'].dt.normalize()
    # 2. 日ごとのTRIMP合計を計算 (1日2回走った場合などを合算)
    daily_groups = df.groupby('day')['trimp'].sum()

    # 3. 日付範囲を再構築 (休んだ日=TRIMP 0 の行を作る！)
    #    これがないとMonotonyの標準偏差が計算できない
    idx = pd.date_range(daily_groups.index.min(), daily_groups.index.max())
    daily_df = daily_groups.reindex(idx, fill_value=0).to_frame(name='trimp')

    # --- 指標計算 (日次データに対して実行) ---

    # (1) CTL & ATL & TSB
    daily_df['ctl'] = daily_df['trimp'].ewm(span=42, adjust=False).mean()
    daily_df['atl'] = daily_df['trimp'].ewm(span=7, adjust=False).mean()
    daily_df['tsb'] = daily_df['ctl'] - daily_df['atl']

    # (2) A:C Ratio (ATL / CTL)
    # ゼロ除算回避のため CTLが0なら0にする
    daily_df['ac_ratio'] = np.where(daily_df['ctl'] > 0, daily_df['atl'] / daily_df['ctl'], 0.0)

    # (3) Monotony (7日間平均 / 7日間標準偏差)
    # rolling mean / rolling std
    r7_mean = daily_df['trimp'].rolling(window=7, min_periods=1).mean()
    r7_std = daily_df['trimp'].rolling(window=7, min_periods=1).std()

    # stdが0（毎日同じTRIMP、または0続き）の場合、Monotonyが高くなりすぎないように制御
    # ここでは便宜上、std=0ならMonotony=0とするか、上限キャップをつける
    daily_df['monotony'] = np.where(r7_std > 0.1, r7_mean / r7_std, 0.0)

    # (4) Training Strain (合計TRIMP * Monotony)
    r7_sum = daily_df['trimp'].rolling(window=7, min_periods=1).sum()
    daily_df['training_strain'] = r7_sum * daily_df['monotony']

    # --- 計算結果を元の詳細データ(df)に戻す ---
    # daily_df は「日付」がインデックスなので、それを結合キーにする
    daily_df.index.name = 'day'

    # dfにマージする (左結合)
    df_merged = pd.merge(df, daily_df, on='day', how='left', suffixes=('', '_daily'))
    # ※ trimp列が重複するので、daily側は計算用に使っただけ。
    # 必要なのは ctl, atl, tsb, ac_ratio, monotony, training_strain

    # (5) Marathon Shape (簡易版ロジック)
    # Logic: CTL(基礎体力) + ロング走ボーナス
    # ロング走ボーナス: 過去10週間で、20km以上走った距離のポイント化
    # ※これはアクティビティ単位で見る必要がある

    # 最近のロング走リスト (過去70日)
    cutoff_date = df_merged['date_dt'].max() - timedelta(days=70)
    long_runs = df_merged[
        (df_merged['date_dt'] >= cutoff_date) &
        (df_merged['distance_km'] >= 20.0)
        ]

    # ロング走スコア計算 (例: トップ3回の距離平均 * 係数)
    long_run_score = 0
    if not long_runs.empty:
        top_3_dist = long_runs['distance_km'].nlargest(3).mean()
        long_run_score = top_3_dist * 2.5  # 係数は適当に調整

    # 現在のMarathon Shape
    current_ctl = daily_df['ctl'].iloc[-1]
    marathon_shape = round(current_ctl + long_run_score, 1)

    # ==========================================
    # 整形 & 返却
    # ==========================================

    # NaN対策
    df_merged = df_merged.fillna(0)


    # ★ ラモス流・完全浄化プロセス
    # DataFrameを辞書リストに変換してから、1つずつ検査して NaN を None に変える
    # これなら Pandas のバージョンや挙動に左右されず確実に消せる
    activities_list = df_merged.to_dict(orient="records")
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
    avg_eff = df_merged['efficiency_score'].mean()

    wk_ago = df_merged['date_dt'].max() - timedelta(days=7)
    recent_df = df_merged[df_merged['date_dt'] >= wk_ago]
    recent_eff = recent_df['efficiency_score'].mean()
    avg_pace = recent_df['pace_min_km'].mean()

    # 統計値が NaN なら 0.0 に置換
    stats = {
        "weekly_volume_km": round(recent_df['distance_km'].sum(), 1),
        "avg_pace": round(avg_pace if not math.isnan(avg_eff) else 0.0, 2),
        "avg_efficiency": round(avg_eff if not math.isnan(avg_eff) else 0.0, 2),
        "recent_efficiency": round(recent_eff if not math.isnan(recent_eff) else 0.0, 2),
        "current_ctl": round(current_ctl, 1),
        "current_tsb": round(daily_df['tsb'].iloc[-1], 1),
        "marathon_shape": marathon_shape
    }

    feedback = "分析完了。"
    if stats["recent_efficiency"] > stats["avg_efficiency"]:
        feedback = "良い傾向だ。効率が上がっている。\n"

    # アドバイス生成
    latest_ac = daily_df['ac_ratio'].iloc[-1]
    if latest_ac > 1.5:
        feedback += "⚠️ 警告：A:C比が1.5を超えている！怪我のリスクが高い。負荷を落とせ。"
    elif latest_ac < 0.8:
        feedback += "負荷が足りない。もっと追い込めるぞ。"
    else:
        feedback += "良い負荷バランスだ。この調子で継続しろ。"


    return {
        "stats": stats,
        "feedback": feedback,
        "activities": clean_activities  # 浄化済みデータを返す
    }

# ★新設: 詳細データ取得API
@app.get("/api/activity/{activity_id}")
def get_activity_details_api(activity_id: int, user_id: int = Depends(get_current_user_id)):
    db_file = f"user_data_{user_id}.db"
    if not os.path.exists(db_file):
        return []  # まだデータがない場合

    # 1. まずDBを確認
    streams = get_activity_stream(activity_id, db_file)
    if streams:
        print(f"Serving activity {activity_id} from DB.")
        return {"activity_id": activity_id, "streams": streams}

    # 2. DBになければGarminから取得
    if os.getenv("USE_REAL_GARMIN") == "True":
        print(f"Fetching activity {activity_id} from Garmin API...")
        try:
            streams = fetch_garmin_details(activity_id)
            # DBに保存
            save_activity_stream(activity_id, streams, db_file)
            return {"activity_id": activity_id, "streams": streams}
        except Exception as e:
            print(f"Error fetching details: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=404, detail="Data not found and Garmin sync disabled.")
