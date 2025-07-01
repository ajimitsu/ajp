import numpy as np
from numba import njit, prange
import time

# --- NumPy vectorized version ---
def vectorized_numpy(x, y):
    """
    Vectorized computation using NumPy:
    z = sin(x) + log(y + 1) * sqrt(x^2 + y^2)
    """
    return np.sin(x) + np.log(y + 1) * np.sqrt(x**2 + y**2)

# --- Numba parallel version ---
@njit(parallel=True)
def parallel_numba(x, y):
    """
    Parallelized computation using Numba with multiple CPU cores.
    Assumes x and y are 1D NumPy arrays of the same size.
    """
    z = np.empty_like(x)
    for i in prange(x.size):
        z[i] = np.sin(x[i]) + np.log(y[i] + 1) * np.sqrt(x[i]**2 + y[i]**2)
    return z

# --- Main benchmark ---
if __name__ == "__main__":
    size = 10_000_000
    x = np.linspace(0, 10, size)
    y = np.linspace(0, 5, size)

    # NumPy vectorized
    t1 = time.time()
    z_np = vectorized_numpy(x, y)
    t2 = time.time()
    print(f"NumPy vectorized time: {t2 - t1:.4f} sec")

    # Numba parallel
    t3 = time.time()
    z_nb = parallel_numba(x, y)
    t4 = time.time()
    print(f"Numba parallel time:   {t4 - t3:.4f} sec")

    # Check correctness
    max_diff = np.max(np.abs(z_np - z_nb))
    print(f"Max difference (should be ~0): {max_diff:.2e}")
