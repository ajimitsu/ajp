from typing import List, Any, Callable
import functools

# Custom Exception
class CustomError(Exception):
    pass

# Decorator Example
def log_function_call(func: Callable):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG]  Calling {func.__name__} with args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)
    return wrapper

# Context Manager Example
class FileHandler:
    def __init__(self, filename: str, mode: str):
        self.filename = filename
        self.mode = mode
        self.file = None

    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()

# Base Class with Properties
class Person:
    def __init__(self, name: str, age: int):
        self._name = name
        self._age = age

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if not value:
            raise ValueError("Name cannot be empty.")
        self._name = value

    @property
    def age(self) -> int:
        return self._age

    @age.setter
    def age(self, value: int):
        if value < 0:
            raise ValueError("Age cannot be negative.")
        self._age = value

    def greet(self):
        print(f"Hello, I'm {self._name} and I'm {self._age} years old.")

# Derived Class with *args and **kwargs
class Employee(Person):
    def __init__(self, name: str, age: int, *args, **kwargs):
        super().__init__(name, age)
        self.skills = args
        self.details = kwargs

    def show_skills(self):
        print("Skills:", ", ".join(self.skills))

    def show_details(self):
        print("Details:", self.details)

    @staticmethod
    def company_name() -> str:
        return "TechCorp Inc."

    @classmethod
    def create_intern(cls, name: str):
        return cls(name, 20, "learning", department="Internship")

    @log_function_call
    def work(self, task: str):
        if not task:
            raise CustomError("Task cannot be empty.")
        print(f"{self.name} is working on {task}.")

# List comprehension and lambda usage
def process_numbers(nums: List[int]) -> List[int]:
    squared = list(map(lambda x: x * x, nums))
    return [x for x in squared if x % 2 == 0]

# Main function
def main():
    try:
        emp = Employee("Alice", 30, "Python", "ML", role="Engineer", location="Remote")
        emp.greet()
        emp.show_skills()
        emp.show_details()
        emp.work("AI Model Training")

        # Static and Class Methods
        print("Company:", Employee.company_name())
        intern = Employee.create_intern("Bob")
        intern.greet()

        # List processing
        print("Processed numbers:", process_numbers([1, 2, 3, 4, 5]))

        # Context manager
        with FileHandler("../example.txt", "w") as f:
            f.write("Hello from context manager!")

    except ValueError as ve:
        print("ValueError:", ve)
    except CustomError as ce:
        print("CustomError:", ce)
    except Exception as e:
        print("Unexpected error:", e)

if __name__ == "__main__":
    main()
