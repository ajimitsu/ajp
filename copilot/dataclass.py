class Book:
    def __init__(self, title, author, year):
        self.title = title
        self.author = author
        self.year = year

    def __repr__(self):
        return f"Book(title={self.title}, author={self.author}, year={self.year})"

from dataclasses import dataclass

@dataclass
class Book:
    title: str
    author: str
    year: int