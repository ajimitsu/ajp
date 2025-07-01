from fastapi import FastAPI, HTTPException, Header, Query
from pydantic import BaseModel
from typing import List, Optional
import sqlite3

app = FastAPI()
"""
uvicorn your_filename:app --reload
- Interactive docs: http://localhost:8000/docs
- Or try requests with tools like httpie, Postman, or your browser.

"""


DB_FILE = "tasks.db"
API_TOKEN = "supersecrettoken"  # ← replace this in production!

class Task(BaseModel):
    id: int
    title: str
    done: bool = False

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                done INTEGER NOT NULL
            )
        """)

def auth(token: Optional[str]):
    if token != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

def to_dict(row):
    return {"id": row[0], "title": row[1], "done": bool(row[2])}

init_db()

@app.get("/tasks", response_model=List[Task])
def get_tasks(
    authorization: Optional[str] = Header(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("id"),
    desc: Optional[bool] = Query(False)
):
    auth(authorization)
    query = "SELECT * FROM tasks"
    params = []

    # Search
    if search:
        query += " WHERE title LIKE ?"
        params.append(f"%{search}%")

    # Sorting
    if sort_by not in ("id", "title", "done"):
        raise HTTPException(status_code=400, detail="Invalid sort field")
    query += f" ORDER BY {sort_by} {'DESC' if desc else 'ASC'}"

    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(query, params).fetchall()
        return [to_dict(r) for r in rows]

@app.post("/tasks", response_model=Task)
def create_task(task: Task, authorization: Optional[str] = Header(None)):
    auth(authorization)
    with sqlite3.connect(DB_FILE) as conn:
        try:
            conn.execute("INSERT INTO tasks (id, title, done) VALUES (?, ?, ?)",
                         (task.id, task.title, int(task.done)))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Task ID already exists")
    return task

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: Task, authorization: Optional[str] = Header(None)):
    auth(authorization)
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.execute("UPDATE tasks SET title=?, done=? WHERE id=?",
                           (task.title, int(task.done), task_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, authorization: Optional[str] = Header(None)):
    auth(authorization)
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
    return {"message": f"Task {task_id} deleted."}