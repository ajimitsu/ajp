import numpy as np
from numba import njit, prange, cuda
import time

# Generate large dataset
size = 10_000_000
data = np.random.rand(size)

# NumPy vectorized
def vectorized_computation(arr):
    return np.sin(arr) ** 2 + np.log(arr + 1)

# CPU-parallel Numba version
@njit(parallel=True)
def numba_parallel_computation(arr):
    result = np.empty_like(arr)
    for i in prange(arr.shape[0]):
        result[i] = np.sin(arr[i]) ** 2 + np.log(arr[i] + 1)
    return result

# GPU version with CUDA
@cuda.jit
def cuda_computation(arr, result):
    i = cuda.grid(1)
    if i < arr.size:
        result[i] = math.sin(arr[i]) ** 2 + math.log(arr[i] + 1)

# Run NumPy vectorized
start = time.time()
vec_result = vectorized_computation(data)
print(f"Vectorized NumPy time: {time.time() - start:.4f} sec")

# Run Numba CPU
start = time.time()
cpu_result = numba_parallel_computation(data)
print(f"Numba Parallel CPU time: {time.time() - start:.4f} sec")

# Run CUDA GPU
import math
threads_per_block = 128
blocks_per_grid = (size + (threads_per_block - 1)) // threads_per_block

data_gpu = cuda.to_device(data)
result_gpu = cuda.device_array_like(data)

start = time.time()
cuda_computation[blocks_per_grid, threads_per_block](data_gpu, result_gpu)
cuda.synchronize()
gpu_result = result_gpu.copy_to_host()
print(f"CUDA GPU time: {time.time() - start:.4f} sec")

# Compare results
print("GPU vs NumPy match:", np.allclose(gpu_result, vec_result, atol=1e-6))