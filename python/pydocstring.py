#!/usr/bin/env python3
from string import Template
import re
import os
import ast
import abc

import ibis

from utils import *
from vimenv import *
from asthelper import ClassVisitor, MethodVisitor, ClassInstanceNameExtractor


class InvalidSyntax(Exception):
    pass


class DocstringUnavailable(Exception):
    pass


class Templater:
    def __init__(self, location, indent, style='google'):
        self.style = style
        self.indent = indent
        self.location = location

    def _docstring_helper(self, obj_indent, docstring):
        lines = []
        for line in docstring.split('\n'):
            if re.match('.', line):
                line = concat_(obj_indent, self.indent, line)
            lines.append(line)

        return '\n'.join(lines)

    def get_method_docstring(self, method_indent, args, returns, yields, raises):
        with open(os.path.join(self.location, '..', 'styles/{}-{}.txt'.format(self.style, 'method')), 'r') as f:
            self.template = ibis.Template(f.read())
        docstring = self.template.render(indent=self.indent, args=args,
            raises=raises, returns=returns, yields=yields)
        return self._docstring_helper(method_indent, docstring)

    def get_class_docstring(self, class_indent, attr):
        with open(os.path.join(self.location, '..', 'styles/{}-{}.txt'.format(self.style, 'class')), 'r') as f:
            self.template = ibis.Template(f.read())
        docstring = self.template.render(indent=self.indent, attr=attr)
        return self._docstring_helper(class_indent, docstring)


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

    def _get_sig(self):
        lines = []
        lines_it = self.env.lines_following_cursor()
        sig_line, first_line = next(lines_it)
        indent = re.findall('^(\s*)', first_line)[0]

        lines.append(first_line)

        while not self._is_valid(''.join(lines)):
            try:
                sig_line, line = next(lines_it)
            except StopIteration as e:
                raise InvalidSyntax('Object does not have valid syntax')
            lines.append(line)
        return sig_line, indent

    def _object_tree(self):
        """ Get the source code of the object under cursor. """
        lines = []
        lines_it = self.env.lines_following_cursor()
        sig_line, first_line = next(lines_it)

        lines.append(first_line)

        func_indent = re.findall('^(\s*)', first_line)[0]
        expected_indent = concat_(func_indent, self.env.python_indent)

        valid_sig, _ = self._is_valid(first_line)

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
        elif re.match('^\s*$', line):
            return True

        return False

    def _is_valid(self, lines):
        func = concat_(lines.lstrip(), '\n   pass')
        try:
            tree = ast.parse(func)
            return True, tree
        except SyntaxError as e:
            return False, None

    def write_simple_docstring(self):
        sig_line, indent = self._get_sig()
        docstring = concat(indent, self.templater.indent, '"""  """')
        self.env.append_after_line(sig_line, docstring)

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
        x = ClassInstanceNameExtractor()
        x.visit(tree)
        v = ClassVisitor(x.instance_name)
        v.visit(tree)
        return v.attributes

    def write_docstring(self):
        sig_line, class_indent, tree = self._object_tree()
        attr = self._process_tree(tree)
        docstring = self.templater.get_class_docstring(class_indent, attr)
        self.env.append_after_line(sig_line, docstring)



class Docstring:

    def __init__(self):
        env = VimEnviroment()
        style = env.python_style
        indent = env.python_indent
        location = env.plugin_root_dir
        templater = Templater(location, indent, style)

        self.obj_controller = self._controller_factory(env, templater, style)

    def _controller_factory(self, env, templater, style):
        line = env.current_line
        first_word = re.match('^\s*(\w+).*', line).groups()[0]
        if first_word == 'def':
            return MethodController(env, templater, style=style)
        elif first_word == 'class':
            return ClassController(env, templater, style=style)
        else:
            raise DocstringUnavailable('Docstring cannot be created for selected object')

    def full_docstring(self):
        try:
            self.obj_controller.write_docstring()
        except Exception as e:
            print(concat_('Doctring ERROR: ', e))
    def oneline_docstring(self):
        try:
            self.obj_controller.write_simple_docstring()
        except Exception as e:
            print(concat_('Doctring ERROR: ', e))
