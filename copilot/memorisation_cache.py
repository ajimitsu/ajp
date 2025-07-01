def memoize(func):
    cache = {}
    def wrapper(x):
        if x in cache:
            return cache[x]
        result = func(x)
        cache[x] = result
        return result
    return wrapper

@memoize
def fibonacci(n):
    if n in (0, 1):
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(30))