from dataclasses import dataclass, asdict
import redis
import hashlib
import json
import numpy as np

# Redis setup
r = redis.Redis(host='localhost', port=6379, db=0)


@dataclass(frozen=True)
class PDESettings:
    length: float
    time: float
    dx: float
    dt: float
    alpha: float

    def to_key(self) -> str:
        """Generate a stable hash key from the parameters"""
        data = json.dumps(asdict(self), sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()


def solve_pde(params: PDESettings) -> np.ndarray:
    nx = int(params.length / params.dx)
    nt = int(params.time / params.dt)
    u = np.zeros(nx)
    u[int(nx / 2)] = 1  # Initial condition

    for _ in range(nt):
        u_new = u.copy()
        for i in range(1, nx - 1):
            u_new[i] = u[i] + params.alpha * params.dt / params.dx ** 2 * (u[i + 1] - 2 * u[i] + u[i - 1])
        u = u_new
    return u


def cached_solve(params: PDESettings) -> np.ndarray:
    key = f"pde:{params.to_key()}"
    cached = r.get(key)
    if cached:
        print("✅ Loaded from cache")
        return np.array(json.loads(cached))

    print("⚙️  Solving from scratch...")
    solution = solve_pde(params)
    r.setex(key, 3600, json.dumps(solution.tolist()))  # Cache for 1 hour
    return solution


if __name__ == "__main__":
    config = PDESettings(length=1.0, time=0.01, dx=0.01, dt=0.00005, alpha=1.0)
    u = cached_solve(config)
    print(u)