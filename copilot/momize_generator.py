from functools import lru_cache

@lru_cache(maxsize=128)
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

print([fibonacci(n) for n in range(10)])


def parse_csv(file_path):
    with open(file_path) as f:
        for line in f:
            yield line.strip().split(",")

def stream_errors(file):
    for line in file:
        if "ERROR" in line:
            yield line