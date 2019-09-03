let s:plugin_root_dir = fnamemodify(resolve(expand('<sfile>:p')), ':h')

python3 << EOF
import sys
from os.path import normpath, join
import vim
plugin_root_dir = vim.eval('s:plugin_root_dir')
python_root_dir = normpath(join(plugin_root_dir, '..', 'python'))
sys.path.insert(0, python_root_dir)

settings = {'g:python_indent': '    ', 'g:python_style':'google'}
for k,v in settings.items():
    if k not in vim.current.buffer.vars:
        vim.command('let {} = {}'.format(k, v))

import pydocstring
EOF

function! Docstring()
    python3 pydocstring.final_call()
endfunction

command! -nargs=0 Docstring call Docstring()

