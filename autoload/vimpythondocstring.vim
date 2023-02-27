let s:plugin_root_dir = fnamemodify(resolve(expand('<sfile>:p')), ':h')

python3 << EOF
import sys
from os.path import normpath, join
import vim
plugin_root_dir = vim.eval('s:plugin_root_dir')
scr = join(plugin_root_dir, '..', 'python')
python_root_dir = normpath(join(plugin_root_dir, '..', 'python'))
deps = [scr]
sys.path[0:0] = deps
import pydocstring
EOF

function! s:handle_error(exception)
    echohl ErrorMsg
    echo join(map(split(a:exception, ":")[2:], 'trim(v:val)'), " : ")
    echohl None
endfunction

function! vimpythondocstring#Full()
    try
        python3 pydocstring.Docstring().full_docstring()
    catch
        call s:handle_error(v:exception)
    endtry
endfunction

function! vimpythondocstring#FullTypes()
    try
        python3 pydocstring.Docstring().full_docstring(print_hints=True)
    catch
        call s:handle_error(v:exception)
    endtry
endfunction

function! vimpythondocstring#Oneline()
    try
        python3 pydocstring.Docstring().oneline_docstring()
    catch
        call s:handle_error(v:exception)
    endtry
endfunction
