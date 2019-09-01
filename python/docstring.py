#!/usr/bin/env python3
import regex as re
from string import Template

def test(a, b="ahoj ): # svete"):
    pass

# TODO: class
# TODO: class will have func, 'one_tab' to return indent of one tab more
# TODO: template different docstrings
def google(arguments, funcdef_indent, indent):
    indent1 = ''.join([funcdef_indent, indent])  #  'one tab' more indented than funcdef
    indent2 = ''.join([indent1, indent])

    argstring = '\n'.join(['{ind2}{name}: '.format(ind2=indent2, name=arg) for arg in arguments])
    docstring = '{ind}"""\n{ind}\n{ind}\n{ind}\n{ind}Args:\n{args}\n{ind}\n{ind}Returns:\n{ind2}\n{ind}\n{ind}"""'.format(\
        ind=indent1, ind2=indent2, args=argstring)
    return docstring

def substitute_list(list_name, template, list_):
    result_lines = []
    for line in template.split('\n'):
        match = re.match('#(\w+):\{(.*)\}', line)
        if match:
            list_to_substitute, old_line = match.groups()
            if list_to_substitute == list_name:
                new_lines = []
                for item in list_:
                    new_line = re.sub('(\$\w+)', item, old_line)
                    new_line = bytes(new_line, 'utf-8').decode('unicode_escape')
                    new_lines.append(new_line)
                result_lines.append(''.join(new_lines))
        else:
            result_lines.append(line)
    return '\n'.join(result_lines)

def google_template(arguments, funcdef_indent, indent):
    with open('./google.txt', 'r') as f:
        template = Template(f.read())
    list_not_sub = template.safe_substitute(i=funcdef_indent, i2=indent)
    return substitute_list('args', list_not_sub, arguments)

if __name__ == '__main__':
    print(google_template(['arg1','arg2'],' '*4, ' '*4))
























