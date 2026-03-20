from garminconnect import Garmin
import os
from datetime import datetime, timedelta, date
import pandas as pd
import sqlite3
import json
import traceback
import time
import random
import math

class GarminRunAnalytics():
    def __init__(self, user_id):
        DEFAULT_MAX_HR = 184
        DEFAULT_REST_HR = 48
        DEFAULT_STOPPED_HR = 100
        DEFAULT_GENDER = True  # Male = True, Female = False

        email = os.getenv("GARMIN_EMAIL")
        password = os.getenv("GARMIN_PASSWORD")
        self.user_id = user_id
        self.db_file = f"data/user_data_{user_id}.db"

        if not email or "example.com" in email: return None
        try:
            client = Garmin(email, password)
            client.login()

            self.client = client

            my_gender, max_hr, rest_hr, stopped_hr = self.get_my_heart_specs()

            self.USER_GENDER = my_gender if my_gender else DEFAULT_GENDER
            self.USER_MAX_HR = int(max_hr) if max_hr else DEFAULT_MAX_HR
            self.USER_REST_HR = int(rest_hr) if rest_hr else DEFAULT_REST_HR
            self.USER_STOPPED_HR = int(stopped_hr) if stopped_hr else DEFAULT_STOPPED_HR

        except Exception as e:
            print(f"Garmin Login Error: {e}")
            traceback.print_exc()
            return None


    def get_my_heart_specs(self):
        try:
            client = self.client
            self.my_display_name = client.display_name
            self.my_full_name = client.full_name

            url = "/userprofile-service/userprofile/user-settings"
            my_settings = client.garth.connectapi(url)

            my_gender = my_settings['userData'].get('gender') == 'MALE'

            url = f"/userprofile-service/socialProfile/{self.my_display_name}"
            my_profile = client.garth.connectapi(url)

            self.my_garminId = my_profile['profileId']

            end_date = date.today()
            start_date = end_date - timedelta(days=365 * 3)

            url = f"{client.garmin_connect_rhr_url}/{client.display_name}"
            params = {"fromDate": start_date, "untilDate": end_date}
            heart_rate_data = client.connectapi(url, params=params)

            dict_user_stats = heart_rate_data['allMetrics']['metricsMap']
            df_rhr = pd.DataFrame(dict_user_stats['WELLNESS_RESTING_HEART_RATE'])
            df_max_hr = pd.DataFrame(dict_user_stats['WELLNESS_MAX_HEART_RATE'])

            max_hr = df_max_hr['value'].nlargest(10).iloc[3:].mean()

            today = pd.Timestamp.now().normalize()
            four_weeks_ago = today - pd.Timedelta(weeks=4)
            last_4_weeks_df_rhr = df_rhr[pd.to_datetime(df_rhr['calendarDate']) >= four_weeks_ago]
            rest_hr = last_4_weeks_df_rhr['value'].mean()

            print(f"GENDER: {my_gender}")
            print(f"MAX_HR: {int(max_hr)}")
            print(f"REST_HR: {int(rest_hr)}")

            if max_hr and rest_hr:
                hrr = max_hr - rest_hr
                stopped_hr = rest_hr + hrr * 0.4
                print(f"HRR: {int(hrr)}")
                print(f"STP_HR: {int(stopped_hr)}")
                return my_gender, max_hr, rest_hr, stopped_hr
            else:
                print("❌ データが取れなかった。Garmin Connectでヘルスケア設定を確認しろ！")
                return None, None, None, None

        except Exception as e:
            print(f"❌ エラー発生: {e}")
            traceback.print_exc()
            return None, None, None, None

    def get_my_activities(self):
        """
        自分のアクティビティを全件取得するジェネレーター
        :param client: ログイン済みのGarminClient
        :param batch_size: 1回のリクエストで取る件数（20〜100推奨）
        """
        start = 0
        # limit = 200
        limit = 20

        activities_all = []
        i = 0
        while True:
            try:
                print(f"   ... {start}件目 から {limit}件 を取得中 ...")
                activities = self.client.get_activities(start, limit)


                if not activities:
                    print(f"   🎉 全データ取得完了！ (Total: {start}件付近)")
                    break

                activities_all.extend(activities)

                break
                start += limit

                sleep_time = random.uniform(3.0, 6.0)
                time.sleep(sleep_time)

            except Exception as e:
                print(f"   ❌ エラー発生 (start={start}): {e}")
                # エラー時は安全のためにループを抜ける（無限ループ防止）
                time.sleep(3)
                return

        return activities_all

    def format_activity(self, activities):

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
            efficiency = speed_m_min / avg_hr if current_type in [
                'running', 'treadmill_running', 'trail_running', 'track_running', 'virtual_run'] and avg_hr > 0 else 0
            pitch = activity.get('averageRunningCadenceInStepsPerMinute', 0.0)
            avg_stride = activity.get('avgStrideLength', 0.0)
            fastest_1km_min = round(activity.get('fastestSplit_1000') / 60, 2) if activity.get('fastestSplit_1000') else None
            fastest_1mile_min = round(activity.get('fastestSplit_1609') / 60, 2) if activity.get('fastestSplit_1609') else None
            fastest_5km_min = round(activity.get('fastestSplit_5000') / 60, 2) if activity.get('fastestSplit_5000') else None
            fastest_10km_min = round(activity.get('fastestSplit_10000') / 60, 2) if activity.get('fastestSplit_10000') else None
            calculated_trimp = self.calculate_trimp(duration_min, moving_min, avg_hr, current_type)
            eff_vo2max = self.calculate_eff_vo2max(dist_m, duration_min, moving_min, avg_hr, elapsed_min) if current_type in [
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
        return self.save_activities(parsed_data, headers, self.db_file)

    @staticmethod
    def init_db(db_file_path: str):
        conn = sqlite3.connect(db_file_path)
        c = conn.cursor()

        # サマリー用テーブル
        c.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                activity_id INTEGER PRIMARY KEY,
                runner_id TEXT,
                runner_name TEXT,
                activity_name TEXT,
                description TEXT,
                activity_type TEXT,
                trainning_effect_label TEXT,
                aerobic_te_message TEXT,
                anaerobic_te_message TEXT,            
                date TEXT,
                distance_km REAL,            
                elapsed_min REAL,
                duration_min REAL,
                avg_hr REAL,
                max_hr REAL,
                pace_min_km REAL,
                avg_pitch_spm REAL,
                avg_stride_cm REAL,
                calories REAL,
                speed_m_min REAL,
                fastestSplit_1km REAL,
                fastestSplit_1mile REAL,
                fastestSplit_5km REAL,
                fastestSplit_10km REAL,
                elevation_gain REAL,
                elevation_loss REAL,
                hr_z1 REAL,
                hr_z2 REAL,
                hr_z3 REAL,
                hr_z4 REAL,
                hr_z5 REAL,
                duration_s REAL,
                moving_duration_s REAL,
                elapsed_duration_s REAL,            
                vo2max REAL,
                vertical_oscillation REAL,
                ground_contact_time REAL,
                aerobic_te REAL,
                anaerobic_te REAL,
                efficiency_score REAL,
                trimp REAL,
                eff_vo2max REAL
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
    def save_activities(self, activities_list, headers, db_file_path: str):
        self.init_db(db_file_path)

        if not activities_list: return 0
        conn = sqlite3.connect(db_file_path)
        c = conn.cursor()
        count = 0
        for a in activities_list:
            try:
                columns = ", ".join(headers)
                placeholders = ", ".join(["?" for _ in headers])

                sql = f'''
                    INSERT OR IGNORE INTO activities 
                    ({columns}) 
                    VALUES ({placeholders})
                '''

                values = [a.get(source_key) for source_key in headers]

                c.execute(sql, tuple(values))

                if c.rowcount > 0: count += 1
            except Exception as e:
                traceback.print_exc()
                print(f"Error saving activity: {e}")
        conn.commit()
        conn.close()
        return count

    def calculate_trimp(self, duration_min, moving_min, avg_hr, current_type):
        """
        TRIMP (Training Impulse) を計算する関数
        Banister's TRIMP formulaを使用
        """
        coefficients = {
            "running": 1.0,
            "track_running": 1.0,
            "virtual_run": 0.9,
            "trail_running": 1.1,
            "treadmill_running": 0.9,
            "indoor_cycling": 0.65,
            "cycling": 0.65,
            "swimming": 0.5,
            "walking": 0.3
        }

        # 辞書にないアクティビティはデフォルトで1.0にする
        coeff = coefficients.get(current_type.lower(), 1.0)


        if not duration_min or not avg_hr or avg_hr < self.USER_REST_HR:
            return None

        if not moving_min or moving_min == None:
            moving_min = duration_min

        avg_hr_moving = (avg_hr * duration_min + self.USER_STOPPED_HR * (duration_min - moving_min)) / moving_min

        # 心拍予備能 (Heart Rate Reserve) の割合
        hrr_ratio = (avg_hr_moving - self.USER_REST_HR) / (self.USER_MAX_HR - self.USER_REST_HR)

        # 男女で係数が違う
        b = 1.92 if self.USER_GENDER else 1.67

        if hrr_ratio <= 0.3: return None
        if hrr_ratio > 1.05: hrr_ratio = 1.0

        # 公式: 時間(分) x 強度 x 指数関数的重み付け
        trimp = moving_min * hrr_ratio * 0.64 * math.exp(b * hrr_ratio) * coeff

        return trimp

    def calculate_eff_vo2max(self, dist_m, duration_min, moving_min, avg_hr, elapsed_min=None):
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

        avg_hr_moving = (avg_hr * duration_min + self.USER_STOPPED_HR * (duration_min - moving_min)) / moving_min
        hrr_ratio = (avg_hr_moving - self.USER_REST_HR) / (self.USER_MAX_HR - self.USER_REST_HR)

        if hrr_ratio <= 0.3: return None
        if hrr_ratio > 1.05: hrr_ratio = 1.0

        effective_vo2 = oxygen_cost / hrr_ratio

        correction_factor = 1.0

        return effective_vo2 * correction_factor