import time

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} ran in {end - start:.4f} seconds")
        return result
    return wrapper

@timer
def slow_function():
    time.sleep(2)
    return "Done!"

slow_function()