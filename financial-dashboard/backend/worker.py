import os
import time
import pandas as pd
import random
from celery import Celery
from database import SessionLocal, Job
import json

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app = Celery("worker", broker=broker_url, backend=broker_url)

@celery_app.task(bind=True)
def run_financial_analysis(self, job_id: str, params: dict):
    # DBセッション
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()

    try:
        job.status = "PROCESSING"
        db.commit()

        # --- ここで重い分析処理をシミュレーション ---
        time.sleep(3) # 3秒待機

        # ダミーデータの生成 (PnL, VaR, DD)
        dates = pd.date_range(start="2024-01-01", periods=30).strftime("%Y-%m-%d").tolist()

        # PnL (累積損益)
        pnl_values = [0]
        for _ in range(29):
            pnl_values.append(pnl_values[-1] + random.uniform(-100, 150))

        # Drawdown
        dd_values = [min(0, x - max(pnl_values[:i+1])) for i, x in enumerate(pnl_values)]

        # VaR (Value at Risk) - 日次変動のシミュレーション
        var_values = [random.uniform(50, 200) for _ in range(30)]

        result_data = {
            "summary": {
                "total_pnl": round(pnl_values[-1], 2),
                "max_dd": round(min(dd_values), 2),
                "avg_var": round(sum(var_values)/len(var_values), 2)
            },
            "charts": {
                "dates": dates,
                "pnl": pnl_values,
                "drawdown": dd_values,
                "var": var_values
            }
        }

        job.status = "SUCCESS"
        job.result = result_data
        db.commit()
        return result_data

    except Exception as e:
        job.status = "FAILED"
        job.result = {"error": str(e)}
        db.commit()
        raise e
    finally:
        db.close()