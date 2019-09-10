from enum import Enum
import string

class NoValue(Enum):
     def __repr__(self):
         return '<%s.%s>' % (self.__class__.__name__, self.name)

class ObjectType(NoValue):
    METHOD = 1
    CLASS = 1 

