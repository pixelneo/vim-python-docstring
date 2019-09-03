#!/usr/bin/env python3
from importlib import import_module


class InvalidSyntax(Exception):
    pass


class VimEnviroment:
    def __init__(self):
        self.vim = import_module('vim')

    def get_var(self, name):
        return self.vim.current.buffer.vars[name]

    @property
    def indent(self):
        return self.get_var('g:python_indent')

    def append_after_line(self, line_nr, text):
        for line in reversed(text.split('\n')):
            vim.current.buffer.append(line, line_nr)

    def lines_following_cursor(self):
        import vim
        lines = []
        buffer = vim.current.buffer
        cursor_row = vim.current.window.cursor[0]-1
        current_row = cursor_row
        while True:
            current_row += 1
            yield current_row, buffer[current_row]


class Method:

    def __init__(self, vim_env, templater, max_lines=30, style='google'):
        self.starting_line = vim_env.current.window.cursor[0] - 1
        self.max_lines = max_lines
        self.vim_env = vim_env
        self.templater = templater

    def write_docstring():
        func_indent, args = self._method_data()
        self.templater.template(func_indent, args)

    def _method_data():
        lines = []
        valid = False
        lines_it = self.vim_env.lines_following_cursor()
        counter = 0
        while not valid:
            if counter == self.max_lines:
                raise InvalidSyntax(
                    'The method either invalid or it is on > {} lines.'.format(str(self.max_lines)))
            last_row, line = next(lines_it)
            lines.append(line)
            valid, tree = self._is_valid(''.join(lines))

        arguments = self._arguments(tree)
        func_indent = re.findall('^(\s*)', lines[0])[0]

        return func_indent, arguments

    def _arguments(tree):
        import ast
        try:
            args = []
            for arg in tree.body[0].args.args:
                args.append(arg.arg)
            return args
        except SyntaxError as e:
            raise InvalidSyntax('The method has invalid syntax.')

    def _is_valid(lines):
        import ast
        func = ''.join(lines.lstrip(), '\n   pass')
        try:
            tree = ast.parse(func)
            return True, tree
        except SyntaxError as e:
            return False, None


class Templater:
    def __init__(self, location, indent, style='google'):
        self.re= import_module('re')
        self.os= import_module('os')
        from string import Template
        import re
        import os

        self.style = 'google'
        self.indent = indent
        with open(os.path.join(location, 'styles/{}.txt'.format(self.style)), 'r') as f:
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

    def template(self, funcdef_indent, arguments):
        list_not_sub = self.template.safe_substitute(
            i=funcdef_indent,
            i2=self.indent
        )
        return self._substitute_list('args', list_not_sub, arguments)


class MethodDocGenerator:
    def __init__(self, style):
        self.style = style
        self.method = Method(style)

    def new_docstring(self):  # generates new docstring no matter what
        pass

    def get_doctring(self, context):  # perform suitable docstring action
        pass


def final_call():
    vim_env = VimEnviroment()
    style = vim_env.get_var('g:python_style')
    indent = vim_env.get_var('g:python_indent')
    location = vim_env.get_var('s:plugin_root_dir')

    templater = Templater(location, indent, style)
    method = Method(vim_env, templater)
    method.write_docstring()

def initialize():
    import vim
    settings = {'g:python_indent': '    ', 'g:python_style':'google'}
    for k,v in settings.items():
        if k not in vim.current.buffer.vars:
            vim.command("let {} = '{}'".format(k, v))
initialize()
