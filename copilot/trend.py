from dataclasses import dataclass

@dataclass
class Book:
    title: str
    author: str
    pages: int

for item in collection:
    if item == target:
        break
else:
    print("Target not found")  # Executed only if the loop didn't break

def greet(name: str) -> str:
    return f"Hello, {name}"