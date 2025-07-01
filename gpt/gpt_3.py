class RegistryMeta(type):
    registry = {}

    def __new__(cls, name, bases, dct):
        new_cls = super().__new__(cls, name, bases, dct)
        if name != 'Base':
            cls.registry[name] = new_cls
        return new_cls

class Base(metaclass=RegistryMeta):
    pass

class A(Base):
    pass

class B(Base):
    pass

print(RegistryMeta.registry)
