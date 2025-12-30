from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import json
from database import SessionLocal, Job
from worker import run_financial_analysis
from schemas import JobStatus

app = FastAPI(title="Financial Analytics API")

# CORS設定 (Reactからのアクセス許可)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/submit")
async def submit_job(
    file: UploadFile = File(None),
    params: str = Form(...),
    db: Session = Depends(get_db)
):
    job_id = str(uuid.uuid4())
    params_dict = json.loads(params)

    # DBにジョブ作成
    new_job = Job(id=job_id, status="PENDING")
    db.add(new_job)
    db.commit()

    # CSVファイルがある場合の処理（今回はモックとして保存せずログのみ）
    if file:
        print(f"Received file: {file.filename}")

    # Celeryタスク投入
    run_financial_analysis.delay(job_id, params_dict)

    return {"job_id": job_id, "status": "submitted"}

@app.get("/api/job/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return {"job_id": job_id, "status": "NOT_FOUND"}

    return {
        "job_id": job.id, 
        "status": job.status, 
        "result": job.result
    }