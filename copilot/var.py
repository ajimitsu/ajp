import time
from functools import wraps
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Decorator to log execution time
def timer_and_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Running: {func.__name__}")
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logging.info(f"Completed: {func.__name__} in {elapsed:.2f} sec")
        return result
    return wrapper

# Task Manager Class
class TaskManager:
    def __init__(self):
        self.tasks: List[str] = []

    @timer_and_log
    def add_task(self, task: str):
        if not task.strip():
            raise ValueError("Task cannot be empty.")
        self.tasks.append(task.strip())
        logging.info(f"Task added: '{task.strip()}'")

    @timer_and_log
    def remove_task(self, index: int):
        try:
            removed = self.tasks.pop(index)
            logging.info(f"Task removed: '{removed}'")
        except IndexError:
            logging.error(f"Invalid task index: {index}")
            raise

    @timer_and_log
    def list_tasks(self):
        if not self.tasks:
            logging.info("No tasks in the list.")
        for i, task in enumerate(self.tasks):
            print(f"{i + 1}. {task}")

# Usage
if __name__ == "__main__":
    tm = TaskManager()
    try:
        tm.add_task("Write a blog post")
        tm.add_task("Refactor the API code")
        tm.add_task("  ")
    except ValueError as ve:
        print(f"Validation error: {ve}")
    tm.list_tasks()
    try:
        tm.remove_task(1)
        tm.remove_task(99)  # This will trigger an IndexError
    except IndexError:
        pass
    tm.list_tasks()