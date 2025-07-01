import itertools

def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

a = itertools.islice(fibonacci(), 100)
print(list(a)[-1])

#minimalism
import random

def reservoir_sample(stream, k):
    result = []
    for i, item in enumerate(stream):
        if i < k:
            result.append(item)
        else:
            j = random.randint(0, i)
            if j < k:
                result[j] = item
    return result

from itertools import groupby

def run_length_encode(seq):
    return [(key, sum(1 for _ in group)) for key, group in groupby(seq)]

text_test = 'aaabbccccdd'
b = run_length_encode(text_test)
print(b)

#recursion
def flatten(lst):
    for item in lst:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item

#anagram grouper
from collections import defaultdict

def group_anagrams(words):
    result = defaultdict(list)
    for word in words:
        key = ''.join(sorted(word))
        result[key].append(word)
    return list(result.values())

test = ["tea","ate","bat","tab"]
groups = group_anagrams(test)
print(groups)