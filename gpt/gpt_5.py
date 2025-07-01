def read_large_file(filepath):
    """
    Why use yield?
    Avoids loading the entire file into memory—ideal for large log files or datasets.
    :param filepath:
    :return:
    """
    with open(filepath, 'r') as f:
        for line in f:
            yield line.strip()

for line in read_large_file("bigdata.txt"):
    print(line)


def infinite_counter(start=0):
    """
    Why use yield?
    Perfect for generating data on-the-fly without precomputing or storing everything.
    :param start:
    :return:
    """
    while True:
        yield start
        start += 1

counter = infinite_counter()
for _ in range(5):
    print(next(counter))


def get_lines(file):
    for line in file:
        yield line.strip()

def filter_lines(lines, keyword):
    """
    🔹 Why use yield?
    Allows for streaming filtering — no need to store intermediate results in memory.
    :param lines:
    :param keyword:
    :return:
    """
    for line in lines:
        if keyword in line:
            yield line

with open("access.log") as f:
    for line in filter_lines(get_lines(f), "ERROR"):
        print(line)


def fibonacci(limit):
    """
    🔹 Why use yield?
    Efficient for sequences where you want to generate values up to a certain condition.
    :param limit:
    :return:
    """
    a, b = 0, 1
    while a < limit:
        yield a
        a, b = b, a + b

for num in fibonacci(100):
    print(num)


import csv

def read_csv_in_chunks(filename, chunk_size=1000):
    """
    🔹 Use case: When you have a 10GB CSV file and don’t want to load it all at once.
    :param filename:
    :param chunk_size:
    :return:
    """
    with open(filename, newline='') as f:
        reader = csv.DictReader(f)
        chunk = []
        for row in reader:
            chunk.append(row)
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk  # Yield remaining rows


def normalize_data(rows):
    """
    🔹 Use case: Preprocess and filter data on-the-fly without creating multiple intermediate lists.
    :param rows:
    :return:
    """
    for row in rows:
        row['value'] = float(row['value']) / 100  # simple normalization
        yield row

def filter_invalid(rows):
    for row in rows:
        if row['value'] >= 0:
            yield row

# Usage
data = read_csv_in_chunks("data.csv")
for chunk in data:
    for row in filter_invalid(normalize_data(chunk)):
        print(row)



import requests
import time

def stream_data_from_api():
    """
    🔹 Use case: Real-time dashboards or streaming analytics without memory bloat.
    """
    while True:
        response = requests.get("https://api.example.com/data")
        if response.status_code != 200:
            break
        yield response.json()
        time.sleep(5)  # poll every 5 seconds


def feature_extractor(data_iter):
    """
    🔹 Use case: Transform large corpora (e.g., for NLP tasks) lazily during model training or evaluation.
    :param data_iter:
    :return:
    """
    for row in data_iter:
        features = {
            'length': len(row['text']),
            'has_keyword': 'python' in row['text'].lower()
        }
        yield features


def batch_generator(X, y, batch_size):
    """
    🔹 Use case: Feeding data in mini-batches to ML models without loading entire dataset into memory.
    :param X:
    :param y:
    :param batch_size:
    :return:
    """
    for i in range(0, len(X), batch_size):
        yield X[i:i+batch_size], y[i:i+batch_size]
