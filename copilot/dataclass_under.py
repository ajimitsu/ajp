from dataclasses import dataclass

@dataclass(order=True, frozen=True)
class Task:
    priority: int
    name: str

t1 = Task(1, "debug")
t2 = Task(1, "debug")

print(t1 == t2)       # True → uses __eq__
print(hash(t1))       # Works → needs __hash__ and frozen=True
print(t1 < Task(2, "test"))  # True → uses __lt__
print(t1)             # Task(priority=1, name='debug') → uses __repr__


@dataclass(init=False, repr=False, eq=False)
class Lightweight:
    id: int


@dataclass(frozen=True)
class SimulationParams:
    dx: float = field(metadata={"unit": "meters"})
    dt: float = field(metadata={"unit": "seconds"})

s = SimulationParams(dx=0.01, dt=0.0005)
print(s.__dataclass_fields__["dx"].metadata)

@dataclass
class Job:
    name: str
    internal_id: int = field(init=False)

    def __post_init__(self):
        self.internal_id = hash(self.name)

j = Job("compress_pde")
print(j.internal_id)

@dataclass
class SecretToken:
    username: str
    token: str = field(repr=False, compare=False)

s1 = SecretToken("mitsu", "abc123")
print(s1)  # Token hidden from output

from dataclasses import dataclass, field
from typing import List
import datetime

@dataclass
class User:
    name: str
    roles: List[str] = field(default_factory=lambda: ["viewer"])
    created_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

u = User(name="mitsu")
print(u)