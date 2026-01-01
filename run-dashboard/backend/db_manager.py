import sqlite3
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
            duration_min REAL,
            avg_hr REAL,
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
            aerobic_te REAL,
            anaerobic_te REAL,
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
                (activity_id,runner_id,runner_name,activity_name,description,activity_type,trainning_effect_label,aerobic_te_message,anaerobic_te_message,date,distance_km,duration_min,avg_hr,pace_min_km,avg_pitch_spm,avg_stride_cm,calories,speed_m_min,fastestSplit_1km,fastestSplit_1mile,fastestSplit_5km,fastestSplit_10km,elevation_gain,elevation_loss,hr_z1,hr_z2,hr_z3,hr_z4,hr_z5,aerobic_te,anaerobic_te,efficiency_score)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                    a['activity_id'],
                    a['runner_id'],
                    a['runner_name'],
                    a['activity_name'],
                    a['description'],
                    a['activity_type'],
                    a['trainning_effect_label'],
                    a['aerobic_te_message'],
                    a['anaerobic_te_message'],
                    a['date'],
                    a['distance_km'],
                    a['duration_min'],
                    a['avg_hr'],
                    a['pace_min_km'],
                    a['avg_pitch_spm'],
                    a['avg_stride_cm'],
                    a['calories'],
                    a['speed_m_min'],
                    a['fastestSplit_1000'],
                    a['fastestSplit_1609'],
                    a['fastestSplit_5000'],
                    a['fastestSplit_10000'],
                    a['elevation_gain'],
                    a['elevation_loss'],
                    a['hr_z1'],
                    a['hr_z2'],
                    a['hr_z3'],
                    a['hr_z4'],
                    a['hr_z5'],
                    a['aerobic_te'],
                    a['anaerobic_te'],
                    a['efficiency_score']
                )
            )
            if c.rowcount > 0: count += 1
        except Exception as e: print(f"Error saving activity: {e}")
    conn.commit()
    conn.close()
    return count

def get_all_activities():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM activities WHERE distance_km >= 1.0 ORDER BY date ASC", conn)
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
