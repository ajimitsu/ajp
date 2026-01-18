import sqlite3
import pandas as pd
import os
import json


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
def save_activities(activities_list, headers, db_file_path: str):
    init_db(db_file_path)

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
        except Exception as e: print(f"Error saving activity: {e}")
    conn.commit()
    conn.close()
    return count

def get_all_activities(db_file_path):
    conn = sqlite3.connect(db_file_path)
    df = pd.read_sql("SELECT * FROM activities ORDER BY date ASC", conn)
    conn.close()
    return df

# --- 詳細ストリーム系 ---
def get_activity_stream(activity_id, db_file_path):
    conn = sqlite3.connect(db_file_path)
    c = conn.cursor()
    c.execute("SELECT streams_json FROM activity_streams WHERE activity_id = ?", (activity_id,))
    result = c.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

def save_activity_stream(activity_id, streams_data, db_file_path):
    try:
        conn = sqlite3.connect(db_file_path)
        c = conn.cursor()
        # JSON文字列として保存
        c.execute("INSERT OR REPLACE INTO activity_streams (activity_id, streams_json) VALUES (?, ?)",
                  (activity_id, json.dumps(streams_data)))
        conn.commit()
        print(f"✅ Saved stream for ID: {activity_id} (Path: {db_file_path})")
    except sqlite3.Error as e:
        # エラーが出たら握りつぶさずに叫ばせる
        print(f"🔥 Database Error: {e}")

    finally:
        if conn:
            conn.close()
