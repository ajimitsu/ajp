class Product:
    def __init__(self, name, price):
        self._name = name
        self._price = price  # underscore denotes "intended" as private

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        if value < 0:
            raise ValueError("Price cannot be negative!")
        self._price = value

item = Product("Laptop", 1500)
print(item.price)        # Calls getter
item.price = 1200        # Calls setter