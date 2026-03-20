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
USER_STOPPED_HR = 100   # 仮の値
MALE_GENDER = True  # 男ならTrue, 女ならFalse (係数が違う)

# パスワードハッシュ化設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

origins = [
    "http://localhost:3000",        # PCのフロントエンド (旧)
    "http://localhost:3002",        # PCのフロントエンド (新)
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3002",
    # 👇【重要】スマホからアクセスする時のURLを絶対に入れる！
    "http://172.16.80.225:3000",
    "http://172.16.80.225:3002",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- データベース接続ヘルパー ---

# 1. マスターDB（会員名簿）への接続
def get_master_db():
    conn = sqlite3.connect("data/master_users.db")
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

# init_master_db()

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
        db_filename = f"data/user_data_{user_id}.db"
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


def calculate_trimp(duration_min, moving_min, avg_hr):
    """
    TRIMP (Training Impulse) を計算する関数
    Banister's TRIMP formulaを使用
    """
    if not duration_min or not avg_hr or avg_hr < USER_REST_HR:
        return None

    if not moving_min or moving_min == None:
        moving_min = duration_min

    avg_hr_moving = (avg_hr * duration_min + USER_STOPPED_HR * (duration_min - moving_min)) / moving_min

    # 心拍予備能 (Heart Rate Reserve) の割合
    hrr_ratio = (avg_hr_moving - USER_REST_HR) / (USER_MAX_HR - USER_REST_HR)

    # 男女で係数が違う
    b = 1.92 if MALE_GENDER else 1.67

    if hrr_ratio <= 0.3: return None
    if hrr_ratio > 1.05: hrr_ratio = 1.0

    # 公式: 時間(分) x 強度 x 指数関数的重み付け
    trimp = moving_min * hrr_ratio * 0.64 * math.exp(b * hrr_ratio)

    return trimp

def calculate_eff_vo2max(dist_m, duration_min, moving_min, avg_hr, elapsed_min=None):
    """
    休憩時間が長すぎるデータを除外する機能付き VO2Max計算
    elapsed_min: 経過時間（分）を追加で受け取る
    """
    # 1. 必須データのチェック
    if not dist_m or not duration_min or not avg_hr:
        return None

    if not moving_min:
        moving_min = duration_min

    # 2. 【追加】 止め忘れ検知ガード (Stop Watch Dog)
    # elapsed_min が渡されていて、かつ duration との乖離が大きすぎる場合
    if elapsed_min:
        # 休憩・停止時間が全体の15%を超えていたら「だらだらラン」か「止め忘れ」とみなす
        # (例: 60分走って、合計9分以上止まっていたら除外)
        stop_ratio = (elapsed_min - moving_min) / elapsed_min
        if stop_ratio > 0.15:
            return None

    speed_m_min = dist_m / moving_min

    oxygen_cost = (0.182258 * speed_m_min) + \
                  (0.000104 * (speed_m_min ** 2)) - \
                  4.60

    if oxygen_cost <= 0: return None

    avg_hr_moving = (avg_hr * duration_min + USER_STOPPED_HR * (duration_min - moving_min)) / moving_min
    hrr_ratio = (avg_hr_moving - USER_REST_HR) / (USER_MAX_HR - USER_REST_HR)

    if hrr_ratio <= 0.3: return None
    if hrr_ratio > 1.05: hrr_ratio = 1.0

    effective_vo2 = oxygen_cost / hrr_ratio

    correction_factor = 1.0

    return effective_vo2 * correction_factor

# --- サマリー同期 ---
def fetch_and_sync_garmin(user_id: int):
    print(f"--- [Background Task] Starting Sync for User ID: {user_id} ---")  # ログ追加

    db_file = f"data/user_data_{user_id}.db"
    if not os.path.exists(db_file):
        return []  # まだデータがない場合

    client = get_garmin_client()
    if not client:
        print("Garmin Client is None. Check env vars.")
        return 0
    try:
        # 直近x件取得
        # activities = client.get_activities(0, 10000)
        # activities = client.get_activities(0, 3000)
        activities = client.get_activities(0, 600)
        parsed_data = []
        for activity in activities:
            # running (ロード), treadmill_running (トレッドミル), trail_running (トレイル), track_running (トラック)
            # これら全てを「ランニング」として認める。
            current_type = activity['activityType']['typeKey']
            # if current_type not in ['running', 'treadmill_running', 'trail_running', 'track_running', 'virtual_run']:
            #     continue
            dist_m = activity.get('distance', 0)
            duration_s = activity.get('duration', 0)
            avg_hr = activity.get('averageHR', 0)

            max_hr = round(activity.get('maxHR'), 0) if activity.get('maxHR') else None
            moving_duration_s = round(activity.get('movingDuration'),2)  if activity.get('movingDuration') else None
            elapsed_duration_s = round(activity.get('elapsedDuration'),2)  if activity.get('elapsedDuration') else None
            vo2max = round(activity.get('vO2MaxValue'),1) if activity.get('vO2MaxValue') else None
            vertical_oscillation = round(activity.get('verticalOscillation'), 2)  if activity.get('verticalOscillation') else None
            ground_contact_time = round(activity.get('groundContactTime'), 2)  if activity.get('groundContactTime') else None

            # if dist_m == 0 or avg_hr == 0: continue
            dist_km = dist_m / 1000
            duration_min = duration_s / 60 if duration_s else 0
            elapsed_min = elapsed_duration_s / 60 if elapsed_duration_s else 0
            moving_min = moving_duration_s / 60 if moving_duration_s else 0
            pace_min_km = duration_min / dist_km if dist_km > 0 else 0
            speed_m_min = dist_m / duration_min if duration_min > 0 else 0
            efficiency = speed_m_min / avg_hr if avg_hr > 0 else 0
            pitch = activity.get('averageRunningCadenceInStepsPerMinute', 0.0)
            avg_stride = activity.get('avgStrideLength', 0.0)
            fastest_1km_min = round(activity.get('fastestSplit_1000') / 60, 2) if activity.get('fastestSplit_1000') else None
            fastest_1mile_min = round(activity.get('fastestSplit_1609') / 60, 2) if activity.get('fastestSplit_1609') else None
            fastest_5km_min = round(activity.get('fastestSplit_5000') / 60, 2) if activity.get('fastestSplit_5000') else None
            fastest_10km_min = round(activity.get('fastestSplit_10000') / 60, 2) if activity.get('fastestSplit_10000') else None
            calculated_trimp = calculate_trimp(duration_min, moving_min, avg_hr)
            eff_vo2max = calculate_eff_vo2max(dist_m, duration_min, moving_min, avg_hr, elapsed_min) if current_type in ['running', 'treadmill_running', 'trail_running', 'track_running', 'virtual_run'] else None

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
                "distance_km": dist_km,
                "duration_s": duration_s,
                "elapsed_min": elapsed_min,
                "duration_min": duration_min,
                "avg_hr": avg_hr,
                "max_hr": max_hr,
                "moving_duration_s": moving_duration_s,
                "elapsed_duration_s": elapsed_duration_s,
                "vo2max": vo2max,
                "vertical_oscillation": vertical_oscillation,
                "ground_contact_time": ground_contact_time,
                "pace_min_km": pace_min_km,
                "avg_pitch_spm": pitch,
                "avg_stride_cm": avg_stride,
                "calories": activity['calories'],
                "speed_m_min": speed_m_min,
                "fastestSplit_1km": fastest_1km_min,
                "fastestSplit_1mile": fastest_1mile_min,
                "fastestSplit_5km": fastest_5km_min,
                "fastestSplit_10km": fastest_10km_min,
                "elevation_gain": round(activity.get('elevationGain'), 1) if activity.get('elevationGain') else 0.0,
                "elevation_loss": round(activity.get('elevationLoss'), 1) if activity.get('elevationLoss') else 0.0,
                "hr_z1": round(activity['hrTimeInZone_1'] / 60, 2) if activity.get('hrTimeInZone_1') else 0.0,
                "hr_z2": round(activity['hrTimeInZone_2'] / 60, 2) if activity.get('hrTimeInZone_2') else 0.0,
                "hr_z3": round(activity['hrTimeInZone_3'] / 60, 2) if activity.get('hrTimeInZone_3') else 0.0,
                "hr_z4": round(activity['hrTimeInZone_4'] / 60, 2) if activity.get('hrTimeInZone_4') else 0.0,
                "hr_z5": round(activity['hrTimeInZone_5'] / 60, 2) if activity.get('hrTimeInZone_5') else 0.0,
                "aerobic_te": round(activity['aerobicTrainingEffect'], 2) if activity.get('aerobicTrainingEffect') else 0.0,
                "anaerobic_te": round(activity['anaerobicTrainingEffect'], 2) if activity.get('anaerobicTrainingEffect') else 0.0,
                "efficiency_score": round(efficiency, 2)  if efficiency else 0.0,
                "trimp": round(calculated_trimp, 1) if calculated_trimp else 0.0,
                "eff_vo2max": round(eff_vo2max, 2) if eff_vo2max else 0.0
            })

        headers = list(parsed_data[0].keys())
        return save_activities(parsed_data, headers, db_file)
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

# --- API Endpoints ---
@app.get("/api/sync")
def trigger_sync(background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id)
                 ):
    background_tasks.add_task(fetch_and_sync_garmin, user_id)
    print(f"Sync request received for User ID: {user_id}")  # ログ確認用
    return {"message": "Sync started in background"}


def generate_training_advice(current_ctl, avg_vo2max, weekly_distance, weekly_trimp, target_time_str="Sub 3.5"):
    """
    現在のCTLと目標タイムから、今週の推奨TRIMPを計算する鬼コーチロジック
    """

    # 1. 目標設定のマッピング
    benchmarks = {
        # --- エリート市民ランナーの壁 (月間 350-450km) ---
        "Sub 2:50": {"target_ctl": 115, "min_vo2": 62, "desc": "ガチ勢。スピードとスタミナの完全融合が必要。"},

        # --- サブ3の聖域 (月間 300-400km) ---
        "Sub 3": {"target_ctl": 100, "min_vo2": 58, "desc": "市民ランナーの勲章。誤魔化しが効かない領域。"},
        "Sub 3:00": {"target_ctl": 100, "min_vo2": 58, "desc": "市民ランナーの勲章。誤魔化しが効かない領域。"},

        # --- 上級者の入り口 (月間 250-350km) ---
        "Sub 3.25": {"target_ctl": 85, "min_vo2": 54, "desc": "サブ3.5を卒業した猛者。キロ4:30巡行の安定感。"},
        "Sub 3:15": {"target_ctl": 85, "min_vo2": 54, "desc": "サブ3.5を卒業した猛者。キロ4:30巡行の安定感。"},

        # --- 本格派ランナーの基準 (月間 200-300km) ---
        "Sub 3.5": {"target_ctl": 75, "min_vo2": 49, "desc": "脱・初心者。LSDだけでなく閾値走(LT)が必須になる。"},
        "Sub 3:30": {"target_ctl": 75, "min_vo2": 49, "desc": "脱・初心者。LSDだけでなく閾値走(LT)が必須になる。"},

        # --- 中級者の壁 (月間 150-250km) ---
        "Sub 3.75": {"target_ctl": 65, "min_vo2": 45, "desc": "歩かずに完走するスタミナと、基礎スピードの向上。"},
        "Sub 3:45": {"target_ctl": 65, "min_vo2": 45, "desc": "歩かずに完走するスタミナと、基礎スピードの向上。"},

        # --- サブ4 (月間 120-200km) ---
        "Sub 4": {"target_ctl": 55, "min_vo2": 41, "desc": "多くのランナーの第一目標。継続的なジョグ習慣の証明。"},
        "Sub 4:00": {"target_ctl": 55, "min_vo2": 41, "desc": "多くのランナーの第一目標。継続的なジョグ習慣の証明。"},

        # --- 完走＋α (月間 100-150km) ---
        "Sub 4:15": {"target_ctl": 45, "min_vo2": 38, "desc": "ハーフマラソンを余裕を持って走れる基礎体力。"},
        "Sub 4:30": {"target_ctl": 38, "min_vo2": 36, "desc": "30kmの壁を越えるための最低限の走り込み。"},

        # --- 完走狙い (月間 60-100km) ---
        "Finish": {"target_ctl": 30, "min_vo2": 34, "desc": "まずは怪我なく42km動き続ける身体作り。"}
    }



    target_data = benchmarks.get(target_time_str, benchmarks["Sub 4"])
    target_ctl = target_data["target_ctl"]
    target_vo2max = target_data["min_vo2"]

    # ★ラモス流・安全係数★
    # 足底筋膜炎のリスクを考慮し、CTLが低いときほど慎重に
    ramp_factor = 30  # 基本は +30 TRIMP

    # 推奨される1日のTRIMP (Current CTL + 30)
    daily_target = current_ctl + ramp_factor

    # 週間目標 (単純計算)
    weekly_target = daily_target * 7


    # 2. ギャップ分析
    ctl_gap = target_ctl - current_ctl
    vo2_gap = target_vo2max - avg_vo2max
    trimp_gap = weekly_target - weekly_trimp


    advice = {}

    if ctl_gap <= 0 and vo2_gap <= 0:
        # 目標CTLに到達している場合
        advice["status"] = "MAINTAIN"
        advice["daily_trimp_target"] = round(current_ctl)  # 維持でOK
        advice["daily_vo2max_target"] = round(avg_vo2max)  # 維持でOK
        advice[
            "message"] = f"{target_time_str}: CTL/VO2Maxは目標の{target_ctl}/{target_vo2max} に到達しているぞ！今は調整期か？無理に上げすぎず、強度（Pace/Interval）を磨け。今週の週合計 TRIMP {round(weekly_target)} で今週は{round(trimp_gap)}足りてない。"


    else:
        # まだ足りない場合（ビルドアップ期）
        advice["status"] = "BUILD"
        advice["daily_trimp_target"] = round(daily_target)
        advice["weekly_trimp_target"] = round(weekly_target)

        advice["message"] = (
            f"目標の{target_time_str}: CTL/VO2Maxは目標の{target_ctl}/{target_vo2max} にはまだ基礎体力が足りん！\n"
            f"継続的な走力向上には週合計 TRIMP {round(weekly_target)}が目標で、"
            f"1日あたり平均 TRIMP {round(daily_target)} だ。今週は{round(trimp_gap)}足りてない。\n"
            f"急に増やすなよ？怪我したら元も子もないからな。"
        )

    return advice




@app.get("/api/dashboard")
def get_dashboard_data(user_id: int = Depends(get_current_user_id)):

    db_file = f"data/user_data_{user_id}.db"
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
    training_strain = daily_df['training_strain'].iloc[-1]


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
    # df_merged = df_merged.fillna(0)


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
    three_month_ago = datetime.now() - timedelta(days=90)
    month_df = df_merged[df_merged['date_dt'] >= three_month_ago]
    avg_eff = month_df['efficiency_score'].nlargest(5).mean()

    week_ago = datetime.now() - timedelta(days=7)
    recent_df = df_merged[df_merged['date_dt'] >= week_ago]


    valid_eff_df = df_merged[
        (df_merged['efficiency_score'].notna()) &
        (df_merged['efficiency_score'] > 0)
        ]

    # 2. 日付の新しい順（降順）に並べ替えて、上から5つだけ取る (Sort & Head)
    target_runs = valid_eff_df.sort_values('date_dt', ascending=False).head(5)

    # 3. その5つの平均を計算する
    recent_eff = target_runs['efficiency_score'].mean()
    avg_pace = recent_df['pace_min_km'].mean()


    avg_vo2max = month_df['vo2max'].nlargest(5).mean()
    avg_eff_vo2max = month_df['eff_vo2max'].nlargest(5).mean()

    weekly_distance = recent_df['distance_km'].sum()
    weekly_trimp = recent_df['trimp'].sum()
    feedback = "分析完了。\n"

    target_time_str = "Sub 3.5"
    running_advice = generate_training_advice(current_ctl, avg_eff_vo2max, weekly_distance, weekly_trimp, target_time_str)
    feedback += running_advice["message"] + "\n"


    if recent_eff > avg_eff:
        feedback += f"心肺機能が上がっている。直近のランニングエコノミー{round(recent_eff,2)}で３か月平均値{round(avg_eff,2)}を上回っている。\n"
    else:
        feedback += f"心肺機能が落ちている。直近のランニングエコノミー{round(recent_eff,2)}で３か月平均値{round(avg_eff,2)}を下回っている。\n"

    # アドバイス生成
    latest_ac = daily_df['ac_ratio'].iloc[-1]
    if latest_ac > 1.5:
        feedback += "⚠️ 警告：A:C比が1.5を超えている！怪我のリスクが高い。トレーニング負荷を落とせ。"
    elif latest_ac < 0.8:
        feedback += "トレーニング負荷が足りない。もっと追い込めるぞ。"
    else:
        feedback += "トレーニング負荷は良いバランスだ。この調子で継続しろ。"


    # 統計値が NaN なら 0.0 に置換
    stats = {
        "weekly_volume_km": round(weekly_distance, 2),
        "weekly_trimp": round(weekly_trimp, 2),
        "avg_pace": round(avg_pace if not math.isnan(avg_eff) else 0.0, 2),
        "avg_efficiency": round(avg_eff if not math.isnan(avg_eff) else 0.0, 2),
        "recent_efficiency": round(recent_eff if not math.isnan(recent_eff) else 0.0, 2),
        "latest_ac": round(latest_ac, 1),
        "training_strain": round(training_strain, 0),
        "current_ctl": round(current_ctl, 1),
        "current_tsb": round(daily_df['tsb'].iloc[-1], 1),
        "vo2max": round(avg_vo2max if not math.isnan(avg_vo2max) else 0.0, 2),
        "eff_vo2max": round(avg_eff_vo2max if not math.isnan(avg_eff_vo2max) else 0.0, 2),
        "marathon_shape": marathon_shape
    }




    return {
        "stats": stats,
        "feedback": feedback,
        "activities": clean_activities  # 浄化済みデータを返す
    }

# ★新設: 詳細データ取得API
@app.get("/api/activity/{activity_id}")
def get_activity_details_api(activity_id: int, user_id: int = Depends(get_current_user_id)):
    db_file = f"data/user_data_{user_id}.db"
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
