import ast
from itertools import chain


class RaiseNameCollector(ast.NodeVisitor):
    def __init__(self):
        self.data = set()
        super().__init__()

    def visit_Call(self, node):
        self.data.add(node.func.id)


class AttributeCollector(ast.NodeVisitor):
    def __init__(self, instance_name):
        self.instance_name = instance_name
        self.data = set()
        super().__init__()

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            if node.value.id == self.instance_name:
                self.data.add(node.attr)
        else:
            self.generic_visit(node)


class ClassInstanceNameExtractor(ast.NodeVisitor):
    def __init__(self):
        self.instance_name = "self"  # default
        self.set = False
        super().__init__()

    def visit_FunctionDef(self, node):
        if node.name == "__init__":
            self.instance_name = node.args.args[0].arg
            self.set = True
        elif not self.set:
            self.instance_name = node.args.args[0].arg

    def generic_visit(self, node):
        if not self.set:
            super().generic_visit(node)


class ClassVisitor(ast.NodeVisitor):
    def __init__(self, instance_name):
        super().__init__()
        self.attributes = set()
        self.instance_name = instance_name

    def visit_Assign(self, node):
        ac = AttributeCollector(self.instance_name)
        for target in node.targets:
            ac.visit(target)
        self.attributes |= ac.data

    def visit_AnnAssign(self, node):
        ac = AttributeCollector(self.instance_name)
        ac.visit(node.target)
        self.attributes |= ac.data


class MethodVisitor(ast.NodeVisitor):
    """Gathers information about a method

    Attributes:
        arguments: arguments of the method
        parent: indicated whether this method is inside another
        raises: set of raised exceptions
        returns: True if method returns
        yields: True is method yields

    """

    def __init__(self, parent=True):
        self.parent = parent
        self.arguments = []
        self.raises = set()
        self.returns = False
        self.yields = False
        super().__init__()

    def _handle_functions(self, node):
        new_visitor = MethodVisitor(parent=False)
        new_visitor.generic_visit(node)
        self.raises |= new_visitor.raises

        if self.parent:
            for arg in chain(node.args.args, node.args.kwonlyargs):
                type_hint = None
                if arg.annotation is not None:
                    type_hint = ast.unparse(arg.annotation)
                self.arguments.append({"arg": arg.arg, "type": type_hint})
            if len(self.arguments) > 0 and (
                self.arguments[0]["arg"] == "self" or self.arguments[0]["arg"] == "cls"
            ):
                self.arguments.pop(0)

            self.returns = new_visitor.returns
            self.yields = new_visitor.yields

    def visit_Raise(self, node):
        r = RaiseNameCollector()
        r.visit(node)
        self.raises |= r.data
        super().generic_visit(node)

    def visit_Yield(self, node):
        self.yields = True
        super().generic_visit(node)

    def visit_Return(self, node):
        self.returns = True
        super().generic_visit(node)

    def visit_FunctionDef(self, node):
        self._handle_functions(node)

    def visit_AsyncFunctionDef(self, node):
        self._handle_functions(node)
