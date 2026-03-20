import sqlite3
import pandas as pd
import os
import json




# --- 詳細ストリーム系 ---
def get_activity_stream(activity_id, db_file_path):
    conn = sqlite3.connect(db_file_path)
    c = conn.cursor()
    c.execute("SELECT streams_json FROM activity_streams WHERE activity_id = ?", (activity_id,))
    result = c.fetchone()
    conn.close()
    return json.loads(result[0]) if result else None

db_file_path = "C:/Users/mitsu/Documents/git/ajp/run-dashboard/backend/user_data_1.db"
activity_id = "20398198910"


test = get_activity_stream(activity_id, db_file_path)
test1 =1