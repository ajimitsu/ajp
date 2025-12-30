import os

# プロジェクトのルートディレクトリ
BASE_DIR = "financial-dashboard"

# ファイルの内容を定義
files = {
    # ---------------------------------------------------------
    # Docker Environment
    # ---------------------------------------------------------
    "docker-compose.yml": """
version: '3.8'

services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis

  worker:
    build: ./backend
    command: celery -A worker.celery_app worker --loglevel=info
    volumes:
      - ./backend:/app
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
      - backend

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    stdin_open: true
    tty: true
""",

    # ---------------------------------------------------------
    # Backend (FastAPI + Celery)
    # ---------------------------------------------------------
    "backend/requirements.txt": """
fastapi
uvicorn
celery
redis
pandas
sqlalchemy
pydantic
python-multipart
openpyxl
""",

    "backend/Dockerfile": """
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
""",

    "backend/database.py": """
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./financial_app.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime, default=datetime.utcnow)
    result = Column(JSON, nullable=True)

Base.metadata.create_all(bind=engine)
""",

    "backend/schemas.py": """
from pydantic import BaseModel
from typing import List, Optional

class JobSubmit(BaseModel):
    analysis_type: str
    parameters: dict

class JobStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None
""",

    "backend/worker.py": """
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
""",

    "backend/main.py": """
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
""",

    # ---------------------------------------------------------
    # Frontend (React + Recharts + Tailwind Mock)
    # ---------------------------------------------------------
    "frontend/package.json": """
{
  "name": "financial-dashboard",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "axios": "^1.6.0",
    "clsx": "^2.1.0",
    "lucide-react": "^0.300.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "recharts": "^2.10.0",
    "tailwind-merge": "^2.2.0",
    "web-vitals": "^2.1.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  },
  "browserslist": {
    "production": [">0.2%", "not dead", "not op_mini all"],
    "development": ["last 1 chrome version", "last 1 firefox version"]
  }
}
""",

    "frontend/Dockerfile": """
FROM node:18-alpine
WORKDIR /app
COPY package.json .
RUN npm install
RUN npm install react-scripts -g
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
""",

    # React Components (One large file approach for simplicity in generation script context,
    # but structured as individual files is better. Let's do structure.)

    "frontend/src/index.js": """
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""",

    "frontend/src/index.css": """
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #0f172a; /* Slate 900 */
  color: #f8fafc;
  font-family: 'Inter', sans-serif;
}
""",

    # App.js (Main Logic)
    "frontend/src/App.js": """
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Upload, Activity, FileJson, Play, CheckCircle, AlertCircle } from 'lucide-react';

// --- UI Components (Simulating shadcn/ui with Tailwind) ---
const Card = ({ children, className }) => (
  <div className={`bg-slate-800 border border-slate-700 rounded-lg p-6 shadow-xl ${className}`}>{children}</div>
);
const Button = ({ children, onClick, disabled, className }) => (
  <button 
    onClick={onClick} 
    disabled={disabled}
    className={`px-4 py-2 rounded-md font-medium transition-all flex items-center gap-2
      ${disabled ? 'bg-slate-600 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 text-white'} ${className}`}
  >
    {children}
  </button>
);
const Input = ({ ...props }) => (
  <input {...props} className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
);

// --- Main Application ---
function App() {
  const [file, setFile] = useState(null);
  const [jsonParams, setJsonParams] = useState('{"strategy": "mean_reversion", "lookback": 20}');
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null); // PENDING, PROCESSING, SUCCESS, FAILED
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('pnl');

  const API_URL = "http://localhost:8000/api";

  const handleSubmit = async () => {
    const formData = new FormData();
    if (file) formData.append("file", file);
    formData.append("params", jsonParams);

    try {
      const res = await axios.post(`${API_URL}/submit`, formData);
      setJobId(res.data.job_id);
      setStatus("PENDING");
      setResult(null);
    } catch (e) {
      alert("Submission failed");
    }
  };

  // Status Polling
  useEffect(() => {
    if (!jobId || status === "SUCCESS" || status === "FAILED") return;

    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_URL}/job/${jobId}`);
        setStatus(res.data.status);
        if (res.data.status === "SUCCESS") {
          setResult(res.data.result);
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, status]);

  // Data formatting for Recharts
  const getChartData = () => {
    if (!result) return [];
    return result.charts.dates.map((date, i) => ({
      date,
      pnl: result.charts.pnl[i],
      drawdown: result.charts.drawdown[i],
      var: result.charts.var[i]
    }));
  };

  const chartData = getChartData();

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto">
      <header className="mb-10 flex items-center gap-3">
        <Activity className="text-blue-400 w-8 h-8" />
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
          Financial Analytics Dashboard
        </h1>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Controls */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <FileJson className="w-5 h-5 text-slate-400" /> Configuration
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Upload CSV Data</label>
                <div className="border-2 border-dashed border-slate-700 rounded-lg p-4 text-center hover:border-blue-500 transition-colors cursor-pointer relative">
                  <input type="file" onChange={(e) => setFile(e.target.files[0])} className="opacity-0 absolute inset-0 cursor-pointer" />
                  <Upload className="w-6 h-6 mx-auto mb-2 text-slate-500" />
                  <span className="text-sm text-slate-400">{file ? file.name : "Click to upload CSV"}</span>
                </div>
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-1">Strategy Parameters (JSON)</label>
                <textarea 
                  className="w-full bg-slate-950 border border-slate-700 rounded p-3 font-mono text-xs h-32 text-green-400 focus:outline-none focus:border-blue-500"
                  value={jsonParams}
                  onChange={(e) => setJsonParams(e.target.value)}
                />
              </div>

              <Button onClick={handleSubmit} disabled={status === "PENDING" || status === "PROCESSING"} className="w-full justify-center">
                {status === "PROCESSING" ? "Processing..." : "Run Analysis"} <Play className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </Card>

          {/* Status Card */}
          {jobId && (
            <Card>
               <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Job Status</h3>
               <div className="flex items-center gap-3">
                 {status === "PENDING" && <span className="text-yellow-500 font-bold animate-pulse">PENDING</span>}
                 {status === "PROCESSING" && <span className="text-blue-500 font-bold animate-pulse">PROCESSING</span>}
                 {status === "SUCCESS" && <span className="text-emerald-500 font-bold flex items-center gap-1"><CheckCircle className="w-4 h-4" /> COMPLETED</span>}
                 {status === "FAILED" && <span className="text-red-500 font-bold flex items-center gap-1"><AlertCircle className="w-4 h-4" /> FAILED</span>}
               </div>
               <div className="text-xs text-slate-500 mt-2 font-mono">{jobId}</div>
            </Card>
          )}
        </div>

        {/* Right Column: Visualization */}
        <div className="lg:col-span-2">
          {result ? (
            <div className="space-y-6">
              {/* KPIs */}
              <div className="grid grid-cols-3 gap-4">
                <Card className="p-4 bg-slate-800/50 border-emerald-900/50">
                   <div className="text-sm text-slate-400">Total PnL</div>
                   <div className={`text-2xl font-bold ${result.summary.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                     ${result.summary.total_pnl.toLocaleString()}
                   </div>
                </Card>
                <Card className="p-4 bg-slate-800/50 border-red-900/50">
                   <div className="text-sm text-slate-400">Max Drawdown</div>
                   <div className="text-2xl font-bold text-red-400">{result.summary.max_dd}%</div>
                </Card>
                <Card className="p-4 bg-slate-800/50 border-blue-900/50">
                   <div className="text-sm text-slate-400">Avg VaR</div>
                   <div className="text-2xl font-bold text-blue-400">${result.summary.avg_var}</div>
                </Card>
              </div>

              {/* Tabs */}
              <div className="flex gap-2 border-b border-slate-700 pb-2">
                {['pnl', 'dd', 'var'].map(tab => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-1 rounded text-sm font-medium transition-colors ${activeTab === tab ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'}`}
                  >
                    {tab.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Charts */}
              <div className="h-[400px] w-full bg-slate-800/30 rounded-lg p-4 border border-slate-700/50">
                <ResponsiveContainer width="100%" height="100%">
                  {activeTab === 'pnl' ? (
                     <AreaChart data={chartData}>
                       <defs>
                         <linearGradient id="colorPnl" x1="0" y1="0" x2="0" y2="1">
                           <stop offset="5%" stopColor="#34d399" stopOpacity={0.3}/>
                           <stop offset="95%" stopColor="#34d399" stopOpacity={0}/>
                         </linearGradient>
                       </defs>
                       <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                       <XAxis dataKey="date" stroke="#94a3b8" />
                       <YAxis stroke="#94a3b8" />
                       <Tooltip contentStyle={{backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9'}} />
                       <Area type="monotone" dataKey="pnl" stroke="#34d399" fillOpacity={1} fill="url(#colorPnl)" />
                     </AreaChart>
                  ) : activeTab === 'dd' ? (
                     <LineChart data={chartData}>
                       <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                       <XAxis dataKey="date" stroke="#94a3b8" />
                       <YAxis stroke="#94a3b8" />
                       <Tooltip contentStyle={{backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9'}} />
                       <Line type="monotone" dataKey="drawdown" stroke="#f87171" dot={false} />
                     </LineChart>
                  ) : (
                     <LineChart data={chartData}>
                       <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                       <XAxis dataKey="date" stroke="#94a3b8" />
                       <YAxis stroke="#94a3b8" />
                       <Tooltip contentStyle={{backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9'}} />
                       <Line type="monotone" dataKey="var" stroke="#60a5fa" dot={false} />
                     </LineChart>
                  )}
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-700 rounded-lg p-12">
              <Activity className="w-12 h-12 mb-4 opacity-50" />
              <p>Run an analysis to see the results dashboard.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
"""
}

# ディレクトリとファイルを作成
for path, content in files.items():
    full_path = os.path.join(BASE_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip())

print(f"✨ プロジェクト生成完了: {os.path.abspath(BASE_DIR)}")
print("🚀 次のステップ:")
print(f"1. cd {BASE_DIR}")
print("2. docker-compose up --build")
print("3. ブラウザで http://localhost:3000 にアクセス")