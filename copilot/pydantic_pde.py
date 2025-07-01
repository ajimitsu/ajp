from pydantic import BaseModel, Field, validator

class PDESettings(BaseModel):
    length: float = Field(..., gt=0, description="Total domain length")
    time: float = Field(..., gt=0, description="Total simulation time")
    dx: float = Field(..., gt=0, description="Spatial step size")
    dt: float = Field(..., gt=0, description="Time step size")
    alpha: float = Field(..., gt=0, description="Diffusion coefficient")

    @validator("dx")
    def dx_must_be_less_than_length(cls, v, values):
        if "length" in values and v >= values["length"]:
            raise ValueError("dx must be smaller than length")
        return v

    @validator("dt")
    def dt_must_be_less_than_time(cls, v, values):
        if "time" in values and v >= values["time"]:
            raise ValueError("dt must be smaller than time")
        return v


from fastapi import FastAPI, HTTPException
import numpy as np
import json

app = FastAPI()

@app.post("/solve")
def solve_pde(params: PDESettings):
    nx = int(params.length / params.dx)
    nt = int(params.time / params.dt)
    u = np.zeros(nx)
    u[nx // 2] = 1.0  # Initial condition

    for _ in range(nt):
        u_new = u.copy()
        for i in range(1, nx - 1):
            u_new[i] = u[i] + params.alpha * params.dt / params.dx**2 * (u[i+1] - 2*u[i] + u[i-1])
        u = u_new

    return {"solution": u.tolist(), "steps": {"nx": nx, "nt": nt}}


TEST_PAYLOAD = {
  "length": 1.0,
  "time": 0.01,
  "dx": 0.01,
  "dt": 0.00005,
  "alpha": 1.0
}