from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True)
class LogEntry:
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

log = LogEntry("Something happened")
print(log)
# LogEntry(message='Something happened', timestamp='2025-06-23T...')


from dataclasses import dataclass

@dataclass(order=True)
class Job:
    priority: int
    id: int
    description: str = ""

jobs = [
    Job(priority=3, id=104, description="Low priority"),
    Job(priority=1, id=102, description="High priority"),
    Job(priority=2, id=103),
]

for j in sorted(jobs):
    print(j)

from dataclasses import dataclass, asdict
from typing import List

@dataclass
class Item:
    name: str
    value: float

@dataclass
class Basket:
    owner: str
    items: List[Item]

basket = Basket("mitsu", [Item("apple", 1.2), Item("banana", 0.8)])
print(asdict(basket))

