#!/usr/bin/env python3
from string import Template
import re
import os
import ast
import abc

from vimenv import *
from utils import ObjectType


class InvalidSyntax(Exception):
    pass


class DocstringUnavailable(Exception):
    pass


class Templater:
    def __init__(self, location, indent, style='google'):
        self.style = 'google'
        self.indent = indent
        with open(os.path.join(location, '..', 'styles/{}.txt'.format(self.style)), 'r') as f:
            self.template = Template(f.read())

    def _substitute_list(self, list_name, template, list_):
        result_lines = []
        for line in template.split('\n'):
            match = re.match('#(\w+):\{(.*)\}', line)
            if match:
                list_to_substitute, old_line = match.groups()
                if list_to_substitute == list_name:
                    new_lines = []
                    for item in list_:
                        new_line = re.sub('(\$\w+)', item, old_line)
                        new_line = bytes(
                            new_line, 'utf-8').decode('unicode_escape')
                        new_lines.append(new_line)
                    result_lines.append(''.join(new_lines))
            else:
                result_lines.append(line)
        return '\n'.join(result_lines)

    def get_template(self, funcdef_indent, arguments):
        list_not_sub = self.template.safe_substitute(
            i=funcdef_indent,
            i2=self.indent
        )
        # TODO: raises
        args_done = self._substitute_list('args', list_not_sub, arguments)
        raises_done = self._substitute_list('raises', args_done, raises)
        return raises_done


class ObjectWithDocstring(abc.ABC):

    def __init__(self, env, templater, max_lines=30, style='google'):
        self.starting_line = env.current_line_nr
        self.max_lines = max_lines
        self.env = env
        self.templater = templater

    @abc.abstractmethod
    def write_docstring(self):
        """ Method to create a docstring for appropriate object

        Writes the docstring to correct lines in `self.env` object.
        """

    def _object_tree(self):
        """ Get the source code of the object under cursor. """
        lines = []
        lines_it = self.env.lines_following_cursor()
        first_line = next(lines_it)
        lines.append(first_line)

        func_indent = re.findall('^(\s*)', first_line)[0]
        expected_indent = ''.join([func_indent, env.python_indent])
        valid_sig = False
        sig_line = 0

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
            # TODO finish

        # remove func_indent from the beginning of all lines 
        data = ''.join([re.sub('^'+func_indent, '', l) for l in lines])
        try:
            tree = ast.parse(tree)
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

        return False


class MethodController(ObjectWithDocstring):

    def __init__(self, env, templater, max_lines=30, style='google'):
        super().__init__(env, templater, max_lines, style)

    # TODO: set cursor on appropriate position to fill the docstring
    def write_docstring(self):
        sig_line, func_indent, tree = self._object_tree()
        args = self._arguments(tree)
        #TODO
        # raises = #what it raises
        # returns = #does it return?
        # yields = # does it yield

        docstring = self.templater.get_template(func_indent, args)
        self.env.append_after_line(last_row, docstring)

    def _raises(self, tree):
        """ Return what exceptions does the method raises """
        # traverse tree for all exceptions
        pass

    def _returns_or_yields(self, tree):
        """ Method either does not yield or return or it yields or it returns (or both???) """
        pass

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

    def __init__(self, env, templater, max_lines=30, style='google'):
        super().__init__(env, templater, max_lines, style)

    def write_docstring(self):
        last_row, func_indent, args = self._method_data()
        docstring = self.templater.get_template(func_indent, args)
        self.env.append_after_line(last_row, docstring)

    def _attributes(self, tree):
        pass


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


