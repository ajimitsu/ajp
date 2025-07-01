from dataclasses import dataclass
from typing import List
from functools import wraps
import time
import json
import os

# Decorator for timing and logging
def log_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[INFO] Running '{func.__name__}'...")
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"[INFO] '{func.__name__}' finished in {duration:.2f}s")
        return result
    return wrapper

# Data model using @dataclass
@dataclass
class Book:
    title: str
    author: str
    year: int
    genre: str

# Book catalog manager
class BookCatalog:
    def __init__(self, filename: str):
        self.filename = filename
        self.books: List[Book] = self._load_books()

    def _load_books(self) -> List[Book]:
        if not os.path.exists(self.filename):
            return []
        with open(self.filename, 'r') as file:
            data = json.load(file)
        return [Book(**item) for item in data]

    @log_time
    def add_book(self, book: Book):
        self.books.append(book)
        print(f"[ADD] '{book.title}' by {book.author}")

    @log_time
    def search_by_author(self, name: str):
        results = list(filter(lambda b: name.lower() in b.author.lower(), self.books))
        if results:
            for book in results:
                print(f"- {book.title} ({book.year}) by {book.author}")
        else:
            print(f"[NOT FOUND] No books by {name}")

    @log_time
    def remove_book(self, title: str):
        for i, book in enumerate(self.books):
            if book.title.lower() == title.lower():
                removed = self.books.pop(i)
                print(f"[REMOVE] '{removed.title}' removed")
                break
        else:
            print(f"[INFO] Book '{title}' not found")

    def save(self):
        with open(self.filename, 'w') as file:
            json.dump([b.__dict__ for b in self.books], file, indent=2)
        print(f"[SAVE] Catalog saved