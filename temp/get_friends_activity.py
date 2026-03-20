from garminconnect import Garmin
import pandas as pd
import time
import random
import	sqlite3
import json

from main import calculate_trimp, calculate_eff_vo2max
from db_manager import save_activities





def format(df):

    num_act = len(df)

    def dict_to_json(x):
        if isinstance(x, dict) or isinstance(x, list):
            return json.dumps(x, ensure_ascii=False)
        return x

    dict_key_list = set()
    for key in df.keys():
        for i in range(num_act):
            if type(df.iloc[i][key]) == dict or type(df.iloc[i][key]) == list:
                dict_key_list.add(key)

    for dict_key in dict_key_list:
        df[dict_key] = df[dict_key].apply(dict_to_json)

    return df

def get_me_friends(email, password):
    try:
        # 1. ログイン
        client = Garmin(email, password)
        client.login()

        # 2. Display Name (文字列ID) はプロパティに入っている
        my_display_name = client.display_name
        my_full_name = client.full_name

        # 3. Numeric ID (数字ID) を取得する
        # 自分のDisplay Nameを使って、自分のSocial Profileを叩くのが確実だ
        url = f"/userprofile-service/socialProfile/{my_display_name}"
        my_profile = client.garth.connectapi(url)


        # 2. 【重要】メソッドがないので、直接URLを叩く (Internal API)
        conn = client.garth.connectapi("/userprofile-service/socialProfile/connections")
        list_connects = conn["userConnections"]

        db_file = "friends.db"
        df = pd.DataFrame(list_connects)
        df_format = format(df)
        conn = sqlite3.connect(db_file)
        df_format.to_sql('friends_list', conn, if_exists='replace', index=False)
        conn.close()

        return client, my_profile, list_connects




    except AttributeError:
        # client.garth がない場合 (古いバージョンのライブラリ)
        print("⚠️ エラー: ライブラリのバージョンが古いか、構造が違います。")
        print("   'dir(client)' で使える中身を確認してください。")
    except Exception as e:
        print(f"❌ 失敗: {e}")

def get_friends_activities(client, connect_info):
    start = 0
    limit = 50  # 1回に取得する件数 (多すぎるとエラーになるので20-50推奨)

    display_name = connect_info['displayName']
    user_id = connect_info['userId']
    full_name = connect_info['fullName']
    db_file = f"db/{str(user_id)}.db"

    activities_all = []
    while True:
        try:
            print(f"   ... {start}件目から{limit}件を取得中 ...")
            url = f"/activitylist-service/activities/{display_name}?limit={limit}&start={start}"
            activities = client.garth.connectapi(url).get("activityList")

            if not activities:
                print(f"   ✅ {full_name} のデータ収集完了！ (Total: {start}件付近)")
                break

            # # 取得したデータを呼び出し元に返す (yield)
            # for act in activities:
            #     yield act
            activities_all.extend(activities)
            # 次のページへ進む準備
            start += limit
            print(f"   ... {start}件目まで取得中 ...")

            # 【超重要】サーバーへの礼儀（スロットリング）
            # 連続アクセスを防ぐため、1秒〜3秒ランダムに待機する
            # sleep_time = random.uniform(3.0, 6.0)
            sleep_time = random.uniform(6.0, 12.0)
            time.sleep(sleep_time)

        except Exception as e:
            # 相手が「公開範囲：自分のみ」にしていると 403 Forbidden が返ることもある
            print(f"   ❌ 取得失敗 (プライバシー制限の可能性): {e}")
            time.sleep(3)
            return


    df = pd.DataFrame(activities_all)
    df_format = format(df)

    conn = sqlite3.connect(db_file)
    df_format.to_sql('activities', conn, if_exists='append', index=False)
    conn.close()

    return


def get_my_activities(client, my_profile):
    """
    自分のアクティビティを全件取得するジェネレーター
    :param client: ログイン済みのGarminClient
    :param batch_size: 1回のリクエストで取る件数（20〜100推奨）
    """
    start = 0
    limit = 100

    display_name = my_profile['displayName']
    user_id = my_profile['id']
    full_name = my_profile['fullName']
    db_file = f"db/{str(user_id)}.db"


    activities_all = []
    i = 0
    while True:
        try:
            print(f"   ... {start}件目 から {limit}件 を取得中 ...")
            activities = client.get_activities(start, limit)

            if not activities:
                print(f"   🎉 全データ取得完了！ (Total: {start}件付近)")
                break

            activities_all.extend(activities)

            # 次のページへ進める
            start += limit

            sleep_time = random.uniform(6.0, 12.0)
            time.sleep(sleep_time)

        except Exception as e:
            print(f"   ❌ エラー発生 (start={start}): {e}")
            # エラー時は安全のためにループを抜ける（無限ループ防止）
            time.sleep(3)
            return

    df = pd.DataFrame(activities_all)
    df_format = format(df)

    conn = sqlite3.connect(db_file)
    df_format.to_sql('activities', conn, if_exists='replace', index=False)
    conn.close()

def format_activity(activities, db_file):
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
        moving_duration_s = round(activity.get('movingDuration'), 2) if activity.get('movingDuration') else None
        elapsed_duration_s = round(activity.get('elapsedDuration'), 2) if activity.get('elapsedDuration') else None
        vo2max = round(activity.get('vO2MaxValue'), 1) if activity.get('vO2MaxValue') else None
        vertical_oscillation = round(activity.get('verticalOscillation'), 2) if activity.get(
            'verticalOscillation') else None
        ground_contact_time = round(activity.get('groundContactTime'), 2) if activity.get('groundContactTime') else None

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
        eff_vo2max = calculate_eff_vo2max(dist_m, duration_min, moving_min, avg_hr, elapsed_min) if current_type in [
            'running', 'treadmill_running', 'trail_running', 'track_running', 'virtual_run'] else None

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
            "anaerobic_te": round(activity['anaerobicTrainingEffect'], 2) if activity.get(
                'anaerobicTrainingEffect') else 0.0,
            "efficiency_score": round(efficiency, 2) if efficiency else 0.0,
            "trimp": round(calculated_trimp, 1) if calculated_trimp else 0.0,
            "eff_vo2max": round(eff_vo2max, 2) if eff_vo2max else 0.0
        })

    headers = list(parsed_data[0].keys())
    return save_activities(parsed_data, headers, db_file)


def format_details(details, conn_detail):
    # 1. 設計図（metricDescriptors）を取得
    # これが「配列の何番目が何のデータか」を教えてくれる
    activity_id = details.get('activityId', '')
    total_metrics_count = details.get('totalMetricsCount', 0)
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


        v = current_metrics.get('directTimestamp')
        if v > 1000000000000:
            timestamp = v / 1000.0
        else:
            timestamp = v

        if start_time is None: start_time = timestamp
        elapsed_min = (timestamp - start_time) / 60.0


        hr = current_metrics.get('directHeartRate')
        elapsed_duration = current_metrics.get('sumElapsedDuration')
        sum_distance = current_metrics.get('sumDistance')
        sum_moving_distance = current_metrics.get('sumMovingDuration')
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
            "activity_id": activity_id,
            "time_min": round(elapsed_min, 2),
            "hr": hr if hr is not None else None,
            "elapsed_duration": elapsed_duration,
            "sum_distance": sum_distance,
            "sum_moving_distance": sum_moving_distance,
            "pace_min_km": pace_min_km,
            "cadence": cadence if cadence is not None else None,
            "vertical_speed": vertical_speed,
            "stride_m": round(stride / 100, 2) if stride is not None else None
        })

    print(f"Processed {len(processed_streams)} points for activity {activity_id}")

    df = pd.DataFrame(processed_streams)


    df.to_sql("activities", conn_detail, if_exists='append', index=False)

    return


def fetch_details_stealth_mode(client, user_id):

    db_file = f"db/{str(user_id)}.db"
    db_details_file = f"db_details/{str(user_id)}.db"
    conn_detail = sqlite3.connect(db_details_file)
    cursor = conn_detail.cursor()
    create_sql = """
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id INTEGER,
        time_min REAL,
        hr REAL,
        elapsed_duration REAL,
        sum_distance REAL,
        sum_moving_distance REAL,
        pace_min_km REAL,
        cadence REAL,
        vertical_speed REAL,
        stride_m REAL
    );
    """
    cursor.execute(create_sql)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_id ON activities(activity_id);")
    conn_detail.commit()


    # 2. DBから「詳細がまだない (details_json IS NULL)」IDリストを取得
    #    ついでに、すでに活動データがあるものだけを対象にする
    target_ids = []
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT activityId, activityName FROM activities")
        target_ids = cursor.fetchall()

    total_targets = len(target_ids)
    print(f"🎯 詳細データ未取得のアクティビティ: {total_targets} 件")

    if total_targets == 0:
        print("🎉 すべて取得済みです！")
        return

    # 3. ループ処理
    count = 0
    consecutive_errors = 0  # 連続エラー回数 (BAN検知用)
    list_details = []
    for act_id, act_name in target_ids:
        count += 1
        print(f"\n[{count}/{total_targets}] ID:{act_id} ({act_name}) の詳細を取得中...")

        try:
            # --- 【核心】詳細データの取得 ---
            # APIを叩く
            details = client.get_activity_details(act_id)

            # データをJSON文字列に変換
            details_str = json.dumps(details, ensure_ascii=False)
            format_details(details, conn_detail)

        except Exception as e:
            print(f"   ❌ エラー: {e}")
            consecutive_errors += 1

            # もし「429 Too Many Requests」や「403 Forbidden」なら即停止
            if "429" in str(e) or "403" in str(e):
                print("🚨 サーバーに怒られました (Rate Limit)。直ちに停止します！")
                return

            # 連続5回失敗したら、ネット回線の不調かBANの可能性が高いので止める
            if consecutive_errors >= 5:
                print("🚨 連続エラーのため強制終了します。")
                return

        # --- 【重要】 ステルス・ウェイト ---

        # A. 基本休憩 (3〜6秒)
        sleep_time = random.uniform(3.0, 6.0)

        # B. ロング休憩 (20件ごとに 20〜30秒 休む)
        if count % 20 == 0:
            long_sleep = random.uniform(20.0, 30.0)
            print(f"   ☕ コーヒーブレイク... ({int(long_sleep)}秒待機)")
            time.sleep(long_sleep)
        else:
            time.sleep(sleep_time)

    conn_detail.close()
    print("🏁 処理終了")

GARMIN_EMAIL = "mitty.26r2@gmail.com"
GARMIN_PASSWORD= "FvQKL5X6"
# my_user_id = "362454728"
# friend_user_id = "84564573"
# friend_user_id = "83286333"
# friend_user_id = "3113959"
friend_user_ids = "79774348,101777119,11636072,69616600,68203708,94844929,12010474".split(",")

client, my_profile, list_connects = get_me_friends(GARMIN_EMAIL, GARMIN_PASSWORD)
get_my_activities(client, my_profile)
# time.sleep(10)

# fetch_details_stealth_mode(client, my_profile['id'])

for friend_user_id in friend_user_ids:
    # print(friend_user_id)
    fetch_details_stealth_mode(client, friend_user_id)

# for connect_info in list_connects:
    # get_friends_activities(client, connect_info)
    # fetch_details_stealth_mode(client, connect_info['userId'])
    # fetch_details_stealth_mode(client, friend_user_id)
    # time.sleep(100)

# format_activity(activities, db_file)


