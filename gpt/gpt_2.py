import asyncio
from typing import Generator, Any, Callable, Type


# ---------- Metaclass Example ----------
class LoggerMeta(type):
    def __new__(cls, name, bases, dct):
        print(f"[Metaclass] Creating class: {name}")
        return super().__new__(cls, name, bases, dct)

    def __call__(cls, *args, **kwargs):
        print(f"[Metaclass] Instantiating class: {cls.__name__}")
        return super().__call__(*args, **kwargs)


# ---------- Base Class with Metaclass ----------
class BaseWithMeta(metaclass=LoggerMeta):
    def base_method(self):
        return "This method is in a metaclass-controlled base."


# ---------- Generator Function ----------
def number_stream(limit: int) -> Generator[int, None, None]:
    print("[Generator] Starting number stream...")
    for i in range(limit):
        yield i
    print("[Generator] Done.")


# ---------- Coroutine / Async Function ----------
async def simulate_io_task(task_name: str, delay: float) -> str:
    print(f"[Coroutine] {task_name} starting (wait {delay}s)...")
    await asyncio.sleep(delay)
    print(f"[Coroutine] {task_name} finished.")
    return f"{task_name} result"


# ---------- Class using everything else ----------
class Worker(BaseWithMeta):
    def __init__(self, name: str):
        self.name = name

    def run_generator_task(self, limit: int):
        print(f"\n{self.name}'s Generator Output:")
        for num in number_stream(limit):
            print(f"Generated: {num}")

    async def run_async_tasks(self):
        tasks = [
            simulate_io_task("Task A", 1),
            simulate_io_task("Task B", 2),
            simulate_io_task("Task C", 1.5),
        ]
        results = await asyncio.gather(*tasks)
        print(f"\n[Coroutine] All async tasks done: {results}")


# ---------- Main Execution ----------
def main():
    print("=== DEMO START ===")

    # Metaclass, Generator, and Coroutine demo
    worker = Worker("Eve")

    # Run generator
    worker.run_generator_task(limit=5)

    # Run coroutines
    asyncio.run(worker.run_async_tasks())

    print("=== DEMO END ===")


if __name__ == "__main__":
    main()
