# --------------------------------------------------------------------------
# User configuration settings.
# --------------------------------------------------------------------------

import datetime


# Assign a template-loading callable here to enable the {% include %}
# and {% extends %} tags. The callable should accept one or more string
# arguments and either return an instance of the Template class or raise
# a TemplateNotFound exception.
loader = None


# Token delimiters.
delimiters = {
    'print_start': '{{',
    'print_end': '}}',
    'eprint_start': '{{{',
    'eprint_end': '}}}',
    'syntax_start': '{%',
    'syntax_end': '%}',
    'comment_start': '{#',
    'comment_end': '#}',
}


# Builtin functions and variables available in all contexts.
builtins = {
    'delimiters': delimiters,
    'now': datetime.datetime.now,
    'range': range,
}
