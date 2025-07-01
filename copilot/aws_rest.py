"""
POST /aws/s3/sync
Authorization: Bearer 🔒

{
  "bucket": "my-personal-backups",
  "source": "/home/user/backups/"
}
"""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import subprocess
import os
import dotenv

dotenv.load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ALLOWED_BUCKETS = {"my-backup-bucket", "my-dev-logs"}
ALLOWED_PATHS = {"/home/mitsu/backups", "/home/mitsu/projects"}


class SyncRequest(BaseModel):
    bucket: str
    source_path: str


app = FastAPI()


def verify_token(auth: Optional[str]):
    if auth != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def is_safe(bucket: str, source: str):
    return bucket in ALLOWED_BUCKETS and source in ALLOWED_PATHS


@app.post("/aws/s3/sync")
def sync_to_s3(sync: SyncRequest, authorization: Optional[str] = Header(None)):
    verify_token(authorization)

    if not is_safe(sync.bucket, sync.source_path):
        raise HTTPException(status_code=403, detail="Bucket or path not allowed")

    cmd = ["aws", "s3", "sync", sync.source_path, f"s3://{sync.bucket}"]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        with open("sync_log.txt", "a") as log:
            log.write(f"✔️ Synced {sync.source_path} to {sync.bucket}\n")
        return {"message": "Sync completed", "stdout": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.stderr}")