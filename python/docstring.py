#!/usr/bin/env python3
import re
from string import Template


# TODO: class
# TODO: class will have func, 'one_tab' to return indent of one tab more
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
























