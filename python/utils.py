from enum import Enum

class NoValue(Enum):
     def __repr__(self):
         return '<%s.%s>' % (self.__class__.__name__, self.name)

class ObjectType(NoValue):
    METHOD = auto()
    CLASS = auto()

