import sqlite3
from dataclasses import dataclass

# Define the Book as a dataclass
@dataclass
class Book:
    title: str
    author: str
    year: int
    genre: str

# Database handler class
class BookDB:
    def __init__(self, db_name="books.db"):
        self.conn = sqlite3.connect(db_name)
        self._create_table()

    def _create_table(self):
        with self.conn:
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                genre TEXT
            )
            """)

    def add_book(self, book: Book):
        with self.conn:
            self.conn.execute("INSERT INTO books (title, author, year, genre) VALUES (?, ?, ?, ?)",
                              (book.title, book.author, book.year, book.genre))
        print(f"[ADD] '{book.title}' saved to database.")

    def find_by_author(self, name: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, author, year, genre FROM books WHERE author LIKE ?", (f"%{name}%",))
        results = cursor.fetchall()
        if results:
            print(f"[FOUND] Books by {name}:")
            for row in results:
                print(f"- {row[0]} ({row[2]}) [{row[3]}]")
        else:
            print(f"[NOT FOUND] No books by {name}")

    def delete_book(self, title: str):
        with self.conn:
            cursor = self.conn.execute("DELETE FROM books WHERE LOWER(title) = LOWER(?)", (title,))
        print(f"[REMOVE] Deleted {cursor.rowcount} book(s) with title '{title}'.")

    def close(self):
        self.conn.close()

# --- Usage Example ---
if __name__ == "__main__":
    db = BookDB()

    db.add_book(Book("Deep Learning with Python", "François Chollet", 2018, "AI"))
    db.add_book(Book("Zen of Python", "Tim Peters", 2020, "Programming"))
    db.find_by_author("Tim")
    db.delete_book("nonexistent")
    db.close()