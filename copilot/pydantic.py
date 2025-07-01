from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

u = User(name="mitsu", age="30")  # auto-converts str to int

from dataclasses import dataclass, field
from marshmallow_dataclass import class_schema

@dataclass
class Item:
    name: str
    price: float = field(metadata={"required": True})

ItemSchema = class_schema(Item)()

import attr

@attr.s
class Product:
    name = attr.ib()
    price = attr.ib(default=0.0)