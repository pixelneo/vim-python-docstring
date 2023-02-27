#!/usr/bin/env python3
import abc
import ast
import os
import re
from string import Template

import ibis
from asthelper import ClassInstanceNameExtractor, ClassVisitor, MethodVisitor
from utils import *
from vimenv import *


class InvalidSyntax(Exception):
    """Raise when the syntax of processed object is invalid."""

    pass


class DocstringUnavailable(Exception):
    """Raise when trying to process object to which there is no docstring."""

    pass


class Templater:
    """Class used to template the docstrings

    Attributes:
        indent: used indentation
        location: path to styles folder
        style: docstring style
        template: resulting remplate

    """

    def __init__(self, location, indent, style="google"):
        self.style = style
        self.indent = indent
        self.location = location

    def _docstring_helper(self, obj_indent, docstring):
        lines = []
        for line in docstring.split("\n"):
            if re.match(".", line):
                line = concat_(obj_indent, self.indent, line)
            lines.append(line)

        return "\n".join(lines)

    def get_method_docstring(
        self, method_indent, args, returns, yields, raises, print_hints=False
    ):
        with open(
            os.path.join(
                self.location, "..", "styles/{}-{}.txt".format(self.style, "method")
            ),
            "r",
        ) as f:
            self.template = ibis.Template(f.read())
        docstring = self.template.render(
            indent=self.indent,
            args=args,
            hints=print_hints,
            raises=raises,
            returns=returns,
            yields=yields,
        )
        return self._docstring_helper(method_indent, docstring)

    def get_class_docstring(self, class_indent, attr):
        with open(
            os.path.join(
                self.location, "..", "styles/{}-{}.txt".format(self.style, "class")
            ),
            "r",
        ) as f:
            self.template = ibis.Template(f.read())
        docstring = self.template.render(indent=self.indent, attr=attr)
        return self._docstring_helper(class_indent, docstring)


class ObjectWithDocstring(abc.ABC):
    """Represents an object (class, method) with the enviroment in which it is opened

    Attributes:
        env: enviroment class
        starting_line: beggining line of the object on which it works
        templater: templater object

    """

    def __init__(self, env, templater):
        self.starting_line = env.current_line_nr
        self.env = env
        self.templater = templater

    @abc.abstractmethod
    def write_docstring(self, *args, **kwargs):
        """Method to create a docstring for appropriate object

        Writes the docstring to correct lines in `self.env` object.
        """
        pass

    def _get_sig(self):
        lines = []
        lines_it = self.env.lines_following_cursor()
        sig_line, first_line = next(lines_it)
        indent = re.findall(r"^(\s*)", first_line)[0]

        lines.append(first_line)

        while not self._is_valid("".join(lines)):
            try:
                sig_line, line = next(lines_it)
            except StopIteration as e:
                raise InvalidSyntax("Object does not have valid syntax")
            lines.append(line)
        return sig_line, indent

    def _object_tree(self):
        """Get the source code of the object under cursor."""
        lines = []
        lines_it = self.env.lines_following_cursor()
        sig_line, first_line = next(lines_it)

        lines.append(first_line)

        obj_indent = re.findall(r"^(\s*)", first_line)[0]
        expected_indent = concat_(obj_indent, self.env.python_indent)

        valid_sig, _ = self._is_valid(first_line)

        while True:
            try:
                last_row, line = next(lines_it)
            except Exception as e:
                break

            if valid_sig and not self._is_correct_indent(
                lines[-1], line, expected_indent
            ):
                break

            lines.append(line)
            if not valid_sig:
                data = "".join(lines)
                valid_sig, _ = self._is_valid(data)
                sig_line = last_row

        # remove obj_indent from the beginning of all lines
        lines = [re.sub("^" + obj_indent, "", l) for l in lines]
        for i, l in enumerate(reversed(lines)):
            if l.strip() == "":
                lines.pop()
            else:
                break
        if len(lines) == 1:
            lines.append(f"{self.env.python_indent}pass")

        data = "\n".join(lines)
        try:
            tree = ast.parse(data)
        except Exception as e:
            raise InvalidSyntax("Object has invalid syntax.")

        return sig_line, obj_indent, tree

    def _is_correct_indent(self, previous_line, line, expected_indent):
        """Check whether given line has either given indentation (or more)
        or does contain only nothing or whitespaces.
        """
        # Disclaimer: I know this does not check for multiline comments and strings
        # strings ''' <newline> ...<newline>..''' are a problem !!!
        if re.match(r"^" + expected_indent, line):
            return True
        elif re.match(r"^\s*#", line):
            return True
        elif re.match(r"^\s*[\"']{3}", line):
            return True
        elif re.match(r".*\\$", previous_line):
            return True
        elif re.match(r"^\s*$", line):
            return True

        return False

    def _is_valid(self, lines):
        func = concat_(lines.lstrip(), "\n    pass")
        try:
            tree = ast.parse(func)
            return True, tree
        except SyntaxError as e:
            return False, None

    def write_simple_docstring(self):
        """Writes the generated docstring in the enviroment"""
        sig_line, indent = self._get_sig()
        docstring = concat_(indent, self.templater.indent, '"""  """')
        self.env.append_after_line(sig_line, docstring)


class MethodController(ObjectWithDocstring):
    def __init__(self, env, templater):
        super().__init__(env, templater)

    def _process_tree(self, tree):
        v = MethodVisitor()
        v.visit(tree)
        args = list(v.arguments)
        raises = list(v.raises)
        return args, v.returns, v.yields, raises

    # TODO: set cursor on appropriate position to fill the docstring
    def write_docstring(self, print_hints=False):
        sig_line, method_indent, tree = self._object_tree()
        args, returns, yields, raises = self._process_tree(tree)
        docstring = self.templater.get_method_docstring(
            method_indent, args, returns, yields, raises, print_hints
        )
        self.env.append_after_line(sig_line, docstring)


class ClassController(ObjectWithDocstring):
    def __init__(self, env, templater):
        super().__init__(env, templater)

    def _process_tree(self, tree):
        x = ClassInstanceNameExtractor()
        x.visit(tree)
        v = ClassVisitor(x.instance_name)
        v.visit(tree)
        att = [attr_name for attr_name in v.attributes]
        return att

    def write_docstring(self, *args, **kwargs):
        sig_line, class_indent, tree = self._object_tree()
        attr = self._process_tree(tree)
        docstring = self.templater.get_class_docstring(class_indent, attr)
        self.env.append_after_line(sig_line, docstring)


class Docstring:
    """Class used by user to generate docstrings"""

    def __init__(self):
        env = VimEnviroment()
        style = env.python_style
        indent = env.python_indent
        location = env.plugin_root_dir
        templater = Templater(location, indent=indent, style=style)

        self.obj_controller = self._controller_factory(env, templater)

    def _controller_factory(self, env, templater):
        line = env.current_line
        try:
            first_word = re.match(r"^\s*(\w+).*", line).groups()[0]
        except Exception:
            first_word = None
        if first_word == "def":
            return MethodController(env, templater)
        elif first_word == "class":
            return ClassController(env, templater)
        elif first_word == "async":
            second_word_catch = re.match(r"^\s*\w+\s+(\w+).*", line)
            if second_word_catch:
                second_word = second_word_catch.groups()[0]
                if second_word == "def":
                    return MethodController(env, templater)

        raise DocstringUnavailable("Docstring ERROR: Doctring cannot be created for selected object")

    def full_docstring(self, print_hints=False):
        """Writes docstring containing arguments, returns, raises, ..."""
        try:
            self.obj_controller.write_docstring(print_hints=print_hints)
        except Exception as e:
            raise DocstringUnavailable(concat_("Docstring ERROR: ", e))

    def oneline_docstring(self):
        """Writes only a one-line empty docstring"""
        try:
            self.obj_controller.write_simple_docstring()
        except Exception as e:
            raise DocstringUnavailable(concat_("Docstring ERROR: ", e))
