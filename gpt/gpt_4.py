def countdown(n):
    while n > 0:
        yield n
        n -= 1

gen = countdown(3)

print(next(gen))  # 3
print(next(gen))  # 2
print(next(gen))  # 1
# print(next(gen))  # Raises StopIteration
