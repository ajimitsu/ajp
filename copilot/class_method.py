from dataclasses import dataclass, asdict
from typing import Self
import hashlib
import json

@dataclass(frozen=True)
class PDESettings:
    length: float
    time: float
    dx: float
    dt: float
    alpha: float

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Validate and instantiate from a plain dict"""
        if data["length"] <= 0 or data["dx"] <= 0 or data["dx"] >= data["length"]:
            raise ValueError("Invalid spatial configuration.")
        if data["time"] <= 0 or data["dt"] <= 0 or data["dt"] >= data["time"]:
            raise ValueError("Invalid temporal configuration.")
        if data["alpha"] <= 0:
            raise ValueError("Alpha must be positive.")
        return cls(**data)

    def to_key(self) -> str:
        data = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
import redis

r = redis.Redis()
app = FastAPI()

class PDESettingsIn(BaseModel):
    length: float
    time: float
    dx: float
    dt: float
    alpha: float

@app.post("/solve")
def solve_pde_endpoint(params: PDESettingsIn):
    try:
        config = PDESettings.from_dict(params.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    key = f"pde:{config.to_key()}"
    cached = r.get(key)
    if cached:
        return {"solution": json.loads(cached), "cached": True}

    # Solve 1D heat equation
    nx = int(config.length / config.dx)
    nt = int(config.time / config.dt)
    u = np.zeros(nx)
    u[nx // 2] = 1.0

    for _ in range(nt):
        u_new = u.copy()
        for i in range(1, nx - 1):
            u_new[i] = u[i] + config.alpha * config.dt / config.dx**2 * (u[i+1] - 2*u[i] + u[i-1])
        u = u_new

    r.setex(key, 3600, json.dumps(u.tolist()))
    return {"solution": u.tolist(), "cached": False}