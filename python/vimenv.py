import vim

class VimEnviroment:

    def __init__(self):
        settings = {'g:python_indent': '    ', 'g:python_style': 'google'}
        for k, v in settings.items():
            vim.command("let {} = get(g:,'{}', \"{}\")".format(k, v, v))

    def _get_var(self, name):
        return vim.eval(name)

    @property
    def plugin_root_dir(self):
        return self._get_var('s:plugin_root_dir')

    @property
    def python_style(self):
        return self._get_var('g:python_style')

    @property
    def python_indent(self):
        return self._get_var('g:python_indent')

    @property
    def current_line(self):
        return vim.current.window.cursor[0] - 1

    def append_after_line(self, line_nr, text):
        line_nr += 1
        for line in reversed(text.split('\n')):
            vim.current.buffer.append(line, line_nr)

    def lines_following_cursor(self):
        import vim
        lines = []
        buffer = vim.current.buffer
        cursor_row = vim.current.window.cursor[0]-1
        current_row = cursor_row
        while True:
            yield current_row, buffer[current_row]
            current_row += 1
