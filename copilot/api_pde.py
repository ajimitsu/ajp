"""
uvicorn api_pde:app --host 127.0.0.1 --port 8888 --reload

swagger: http://locahost:8888/docs

curl -X POST http://127.0.0.1:8888/solve \
  -H "Content-Type: application/json" \
  -d '{"length": 1.0, "time": 0.01, "dx": 0.01, "dt": 0.00005, "alpha": 1.0}'
"""


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np

app = FastAPI()


# Define parameters for the PDE
class PDESettings(BaseModel):
    length: float = 1.0
    time: float = 0.1
    dx: float = 0.01
    dt: float = 0.0001
    alpha: float = 1.0  # diffusion coefficient

@app.get("/")
def read_root():
    return {"message": "PDE Solver API is up and running!"}


@app.post("/solve")
def solve_pde(params: PDESettings):
    L, T, dx, dt, alpha = params.length, params.time, params.dx, params.dt, params.alpha
    nx = int(L / dx)
    nt = int(T / dt)

    if not (0 < dx < L and 0 < dt < T and alpha > 0):
        raise HTTPException(status_code=400, detail="Invalid PDE parameters.")

    u = np.zeros(nx)
    u[int(nx / 2)] = 1.0  # Initial spike in the center

    for n in range(nt):
        u_new = u.copy()
        for i in range(1, nx - 1):
            u_new[i] = u[i] + alpha * dt / dx ** 2 * (u[i + 1] - 2 * u[i] + u[i - 1])
        u = u_new

    return {"solution": u.tolist(), "spatial_steps": nx, "time_steps": nt}