from dataclasses import dataclass

@dataclass
class Book:
    title: str
    author: str
    year: int
    in_stock: bool = True  # Default value

# Create instances
book1 = Book("Clean Code", "Robert C. Martin", 2008)
book2 = Book("Python Tricks", "Dan Bader", 2017, in_stock=False)

# Access attributes
print(book1.title)      # Clean Code
print(book2.in_stock)   # False

# Comparison and auto-generated __repr__()
print(book1)
print(book1 == book2)   # False

from dataclasses import dataclass

@dataclass
class Counter:
    count: int = 0

c = Counter()
c.count += 1  # ✅ Mutable by default
print(c.count)  # 1

@dataclass(frozen=True)
class FrozenCounter:
    count: int

fc = FrozenCounter(5)
# fc.count += 1  # ❌ Raises FrozenInstanceError

from dataclasses import dataclass

@dataclass(order=True)
class Task:
    priority: int
    name: str

t1 = Task(1, "Write docs")
t2 = Task(2, "Fix bugs")
print(t1 < t2)  # ✅ True, because 1 < 2


from dataclasses import dataclass

@dataclass
class Author:
    name: str

@dataclass
class Book:
    title: str
    year: int
    author: Author

b = Book("Clean Architecture", 2017, Author("Robert C. Martin"))
print(b.author.name)  # Robert C. Martin