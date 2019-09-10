from enum import Enum
import string

class NoValue(Enum):
     def __repr__(self):
         return '<%s.%s>' % (self.__class__.__name__, self.name)

class ObjectType(NoValue):
    METHOD = 1
    CLASS = 1 

class Formatter(string.Formatter):
    # def convert_field(self, value, conversion):
        # if conversion[0] == 'l':
            # return ('\n'+conversion[1:]).join(value)
        # else:
            # return super().convert_field(value, conversion)

    def format_field(self, value, format_spec):
        if format_spec.startswith('list'):
            incl = format_spec.split(':')[-1]
            return '\n'.join(([incl+v for v in value]))
        elif format_spec.startswith('if'):
            if 

        # return ''.join([format_spec, value])


if __name__=='__main__':
    fm = Formatter()
    d = ['darkness']*4

    s = 'prvni\n{args:if:{lst:list:    \n}}'
    print(d)
    print(fm.format(s, lst=d))



