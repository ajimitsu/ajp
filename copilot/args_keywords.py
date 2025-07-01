import time
from functools import wraps

class FunctionLogger:
    def __init__(self):
        self.history = []

    def log(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            call_data = {
                'function': func.__name__,
                'args': args,
                'kwargs': kwargs,
                'execution_time': elapsed
            }
            self.history.append(call_data)
            print(f"[LOG] {func.__name__} called with args={args}, kwargs={kwargs} (took {elapsed:.4f}s)")
            return result
        return wrapper

    def show_history(self):
        print("\n--- Function Call History ---")
        for entry in self.history:
            print(f"{entry['function']}({entry['args']}, {entry['kwargs']}) - {entry['execution_time']:.4f}s")

# Instantiate the logger
logger = FunctionLogger()

# Use the decorator on different functions
@logger.log
def greet(name, greeting="Hello"):
    time.sleep(0.5)
    return f"{greeting}, {name}!"

@logger.log
def add_numbers(*nums):
    time.sleep(0.2)
    return sum(nums)

@logger.log
def update_profile(**info):
    time.sleep(0.3)
    return f"Profile updated: {info}"

# Try them out
print(greet("Mitsu"))
print(add_numbers(10, 20, 30))
print(update_profile(name="Mitsu", mood="learning", location="Sapporo"))

# View log
logger.show_history()