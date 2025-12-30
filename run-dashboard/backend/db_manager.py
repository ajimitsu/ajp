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
