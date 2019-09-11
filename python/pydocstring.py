#!/usr/bin/env python3
from string import Template
import re
import os
import ast
import abc

import ibis

from vimenv import *
from utils import ObjectType
from asthelper import ClassVisitor, MethodVisitor, ClassInstanceNameExtractor


class InvalidSyntax(Exception):
    pass


class DocstringUnavailable(Exception):
    pass


class Templater:
    def __init__(self, location, indent, style='google'):
        self.style = 'google'
        self.indent = indent
        self.location = location

    def get_method_docstring(self, method_indent, args, returns, yields, raises):
        with open(os.path.join(self.location, '..', 'styles/{}-{}.txt'.format(self.style, 'method')), 'r') as f:
            self.template = ibis.Template(f.read())
        docstring = self.template.render(indent=self.indent, args=args,
            raises=raises, returns=returns, yields=yields)
        lines = []
        for line in docstring.split('\n'):
            if re.match('.', line):
                line = ''.join([method_indent, self.indent, line])
            lines.append(line)

        return '\n'.join(lines)

    def get_class_docstring(self, class_indent, attr):
        with open(os.path.join(self.location, '..', 'styles/{}-{}.txt'.format(self.style, 'class')), 'r') as f:
            self.template = ibis.Template(f.read())
        docstring = self.template.render(indent=self.indent, attr=attr)
        lines = []
        for line in docstring.split('\n'):
            if re.match('.', line):
                line = ''.join([method_indent, self.indent, line])
            lines.append(line)

        return '\n'.join(lines)


class ObjectWithDocstring(abc.ABC):

    def __init__(self, env, templater, style='google'):
        self.starting_line = env.current_line_nr
        self.env = env
        self.templater = templater

    @abc.abstractmethod
    def write_docstring(self):
        """ Method to create a docstring for appropriate object

        Writes the docstring to correct lines in `self.env` object.
        """
        pass

    def _object_tree(self):
        """ Get the source code of the object under cursor. """
        lines = []
        lines_it = self.env.lines_following_cursor()
        sig_line, first_line = next(lines_it)

        lines.append(first_line)

        func_indent = re.findall('^(\s*)', first_line)[0]
        expected_indent = ''.join([func_indent, self.env.python_indent])

        valid_sig = self._is_valid(first_line)

        while True:
            try:
                last_row, line = next(lines_it)
            except StopIteration as e:
                break
            if valid_sig and not self._is_correct_indent(lines[-1], line, expected_indent):
                break

            lines.append(line)
            if not valid_sig:
                data = ''.join(lines)
                valid_sig, _ = self._is_valid(data)
                sig_line = last_row

        # remove func_indent from the beginning of all lines 
        data = '\n'.join([re.sub('^'+func_indent, '', l) for l in lines])
        try:
            tree = ast.parse(data)
        except Exception as e:
            raise InvalidSyntax('Object has invalid syntax.')

        return sig_line, func_indent, tree

    def _is_correct_indent(self, previous_line, line, expected_indent):
        """ Check whether given line has either given indentation (or more) 
            or does contain only nothing or whitespaces.
        """
        # Disclaimer: I know this does not check for multiline comments and strings
        # strings ''' <newline> ...<newline>..''' are a problem !!!
        if re.match('^'+expected_indent, line):
            return True
        elif re.match('^\s*#', line):
            return True
        elif re.match('^\s*["\']{3}', line):
            return True
        elif re.match('.*\\$', previous_line):
            return True
        elif re.match('^&', line):
            return True

        return False

    def _is_valid(self, lines):
        func = ''.join([lines.lstrip(), '\n   pass'])
        try:
            tree = ast.parse(func)
            return True, tree
        except SyntaxError as e:
            return False, None

class MethodController(ObjectWithDocstring):

    def __init__(self, env, templater, style='google'):
        super().__init__(env, templater, style)

    def _process_tree(self, tree):
        v = MethodVisitor()
        v.visit(tree)
        return v.arguments, v.returns, v.yields, v.raises

    # TODO: set cursor on appropriate position to fill the docstring
    def write_docstring(self):
        sig_line, method_indent, tree = self._object_tree()
        args, returns, yields, raises = self._process_tree(tree)
        docstring = self.templater.get_method_docstring(method_indent, args, returns, yields, raises)
        self.env.append_after_line(sig_line, docstring)


    def _arguments(self, tree):
        try:
            args = []
            for arg in tree.body[0].args.args:
                args.append(arg.arg)
            if args[0] == 'self' or args[0] == 'cls':
                args.pop(0)
            return args
        except SyntaxError as e:
            raise InvalidSyntax('The method has invalid syntax.')


class ClassController(ObjectWithDocstring):

    def __init__(self, env, templater, style='google'):
        super().__init__(env, templater, style)

    def _process_tree(self, tree):
        x = ClassInstanceNameExtract()
        x.visit(tree)
        v = ClassVisitor(x.instance_name)
        v.visit(tree)
        return v.attributes

    def write_docstring(self):
        sig_line, class_indent, tree = self._object_tree()
        attr = self._process_tree(tree)
        docstring = self.templater.get_class_docstring(class_indent, attr)
        self.env.append_after_line(sig_line, docstring)


# Unused
class MethodDocGenerator:
    def __init__(self, templater, env, style):
        self.object = self._create_object_controller(env, templater, style)

    def _create_object_controller(self, env, templater, style):
        line = self.env.current_line
        first_word = re.match('^\s*(\w+).*', line).groups()[0]
        if first_word == 'def':
            return MethodController(env, templater, style=style)
        elif first_word == 'class':
            return ClassController(env, templater, style=style)
        else:
            raise DocstringUnavailable('Docstring cannot be created for selected object')


    def new_docstring(self):  # generates new docstring no matter what
        pass

    def get_doctring(self, context):  # perform suitable docstring action
        pass


def final_call():
    env = VimEnviroment()
    style = env.python_style
    indent = env.python_indent
    location = env.plugin_root_dir

    templater = Templater(location, indent, style)
    method = MethodController(env, templater)
    method.write_docstring()


