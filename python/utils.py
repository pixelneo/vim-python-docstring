from enum import Enum
import ast

class NoValue(Enum):
     def __repr__(self):
         return '<%s.%s>' % (self.__class__.__name__, self.name)

class ObjectType(NoValue):
    METHOD = auto()
    CLASS = auto()

class MethodProcesser(ast.NodeVisitor):

    def visit_Attribute(node):
        pass

    def visit_Returns(node):
        pass

    def visit_Yield(node):
        pass

    def visit_Raise(node):
        pass

    def visit_arguments(node):


class ClassProcesser(ast.NodeVisitor):

    def visit_FuncDef(node):

        pass

    def visit_A

class
