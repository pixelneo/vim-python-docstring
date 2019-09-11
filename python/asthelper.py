import ast


class NameCollector(ast.NodeVisitor):

    def __init__(self):
        super().__init__()
        self.data = set()

    def visit_Name(self, node):
        self.data.add(node.id)
        super().generic_visit(node)


class ClassInstanceNameExtractor(ast.NodeVisitor):

    def __init__(self):
        self.instance_name = 'self'  # default
        self.set = False
        super().__init__()

    def visit_FunctionDef(self, node):
        if node.name == '__init__':
            self.instance_name = node.args.args[0].arg
            self.set = True

    def generic_visit(self, node):
        if not self.set:
            super().generic_visit(node)


class ClassVisitor(ast.NodeVisitor):
    def __init__(self, instance_name):
        super().__init__()
        self.attributes = set()
        self.instance_name = instance_name

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            if node.value.id == self.instance_name:
                self.attributes.add(node.attr)
        else:
            self.generic_visit(node)


class MethodVisitor(ast.NodeVisitor):
    def __init__(self, parent=True):
        self.parent = parent
        self.arguments = []
        self.raises = set()
        self.returns = False
        self.yields = False
        super().__init__()

    def visit_Raise(self, node):
        r = NameCollector()
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
        new_visitor = MethodVisitor(parent=False)
        new_visitor.generic_visit(node)
        self.raises |= new_visitor.raises

        if self.parent:
            for arg in node.args.args:
                self.arguments.append(arg.arg)
            if self.arguments[0] == 'self' or self.arguments[0] == 'cls':
                self.arguments.pop(0)

            self.returns = new_visitor.returns
            self.yields = new_visitor.yields
