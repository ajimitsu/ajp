nums = [1, 2, 3, 4, 5]
squares = list(map(lambda x: x**2, nums))
print(squares)  # [1, 4, 9, 16, 25]

words = ["apple", "banana", "kiwi", "fig", "mango"]
short_words = list(filter(lambda w: len(w) <= 4, words))
print(short_words)  # ['kiwi', 'fig']

from functools import reduce

values = [1, 2, 3, 4]
product = reduce(lambda x, y: x * y, values)
print(product)  # 24

def double(x): return x * 2
def increment(x): return x + 1

composed = lambda x: double(increment(x))
print(composed(3))  # (3 + 1) * 2 = 8

def add_tax(price: float, rate: float) -> float:
    return price * (1 + rate)

print(add_tax(100, 0.1))  # 110.0

celsius = [0, 10, 20, 30]
fahrenheit = list(map(lambda c: (c * 9/5) + 32, celsius))
print(fahrenheit)  # [32.0, 50.0, 68.0, 86.0]

names = ["mitsu", "yuki", "sora"]
capitalized = list(map(str.title, names))
print(capitalized)  # ['Mitsu', 'Yuki', 'Sora']

def is_prime(n):
    return n > 1 and all(n % i != 0 for i in range(2, int(n ** 0.5) + 1))

nums = list(range(2, 20))
primes = list(filter(is_prime, nums))
print(primes)  # [2, 3, 5, 7, 11, 13, 17, 19]

words = ["python", "", "numba", None, "numpy", ""]
cleaned = list(filter(None, words))
print(cleaned)  # ['python', 'numba', 'numpy']

from functools import reduce

factorial = reduce(lambda x, y: x * y, range(1, 6))
print(factorial)  # 120

words = ["parallel", "vectorization", "cpu", "gpu"]
longest = reduce(lambda a, b: a if len(a) > len(b) else b, words)
print(longest)  # vectorization


from functools import reduce

# Sample data: a list of book dictionaries
books = [
    {"title": "Zen and the Art of Motorcycle Maintenance", "year": 1974},
    {"title": "The Pragmatic Programmer", "year": 1999},
    {"title": "Clean Code", "year": 2008},
    {"title": "Deep Learning with Python", "year": 2017},
    {"title": "Automate the Boring Stuff", "year": 2015},
]

# Step 1: Filter books published after 2000
recent_books = list(filter(lambda b: b["year"] > 2000, books))

# Step 2: Map to extract (title, title_length)
title_lengths = list(map(lambda b: (b["title"], len(b["title"])), recent_books))

# Step 3: Reduce to calculate total title character count
total_chars = reduce(lambda acc, b: acc + b[1], title_lengths, 0)

# Output the steps
print("Filtered Books:")
for title, length in title_lengths:
    print(f"- {title} ({length} characters)")

print(f"\nTotal characters in recent book titles: {total_chars}")