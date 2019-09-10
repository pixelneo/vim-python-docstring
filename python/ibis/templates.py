# --------------------------------------------------------------------------
# The Template class is the public interface to the template engine.
#
# A Template object is initialized with a template string. It compiles the
# string and stores the resulting tree of template nodes. A compiled
# template can be rendered multiple times by calling its render() method
# with a dictionary of key-value pairs or a set of keyword arguments.
# --------------------------------------------------------------------------

import re
import collections

from . import config
from . import nodes

from .errors import Undefined, InvalidTag, NestingError


class Template:

    """ Public interface to the template engine. """

    def __init__(self, string):
        self.root = self._parse(Lexer(string))
        self.registry = self._register_blocks(self.root, {})

    def __repr__(self):
        return repr(self.root)

    def render(self, *pargs, **kwargs):
        """ Accepts a data dictionary or a set of keyword arguments. """
        data = pargs[0] if pargs else kwargs
        return self.root.render(Context(data, self))

    def _parse(self, tokens):
        """ Compiles a sequence of tokens into a tree of nodes.

        Syntax nodes with block scope remain on the stack until we
        encounter the corresponding end tag in the token stream. We
        then pop the stack and call .exit_scope() on the block node
        so it can process its child nodes.

        """
        root = nodes.nodemap['root']()
        stack, expecting = [root], []

        for token in tokens:
            if token.type == 'syntax':
                if token.tag in nodes.nodemap:
                    node = nodes.nodemap[token.tag](token)
                elif token.tag in nodes.nodemap['endtags']:
                    if not expecting:
                        raise NestingError('not expecting [%s]' % token.tag)
                    elif token.tag == expecting[-1]:
                        stack[-1].exit_scope()
                        stack.pop()
                        expecting.pop()
                        continue
                    else:
                        msg = 'expecting [%s], found [%s]'
                        raise NestingError(msg % (expecting[-1], token.tag))
                else:
                    msg = '[%s] is not a recognised template tag'
                    raise InvalidTag(msg % token.tag)
            else:
                node = nodes.nodemap[token.type](token)
            stack[-1].children.append(node)
            if node.end_tag:
                stack.append(node)
                expecting.append(node.end_tag)

        if expecting:
            raise NestingError('expecting [%s]' % expecting[-1])

        return stack.pop()

    def _register_blocks(self, node, registry):
        """ Assembles a registry of the template's {% block %} nodes.

        This function walks the node tree and assembles a dictionary
        containing lists of block nodes indexed by title. We use this list
        to implement template inheritance - a block node occurring later in
        a list overrides those occuring earlier.

        Note that we don't implement template inheritance by modifying the
        block nodes in situ. This is because templates can incorporate
        multiple (possibly-cached) sub-templates, so a single block node
        instance can form part of multiple distinct template trees.

        """
        if isinstance(node, nodes.nodemap['block']):
            registry.setdefault(node.title, []).append(node)
        for child in node.children:
            self._register_blocks(child, registry)
        return registry


class Context:

    """ Implements the template engine's variable lookup logic. """

    def __init__(self, data, template):

        # Data is stored on a stack of dictionaries.
        self.stack = []

        # Standard builtins.
        self.stack.append({'context': self, 'defined': self.defined})

        # User-configurable, per-application builtins.
        self.stack.append(config.builtins)

        # Instance-specific data.
        self.stack.append(data)

        # Nodes can store state information here to avoid threading issues.
        self.stash = {}

        # This reference gives nodes access to their parent template object.
        self.template = template

    def __setitem__(self, key, value):
        """ Assigns to the last dictionary on the stack. """
        self.stack[-1][key] = value

    def __getitem__(self, key):
        """ Checks every dictionary on the stack for `key`. """
        for d in reversed(self.stack):
            if key in d:
                return d[key]
        raise KeyError(key)

    def __delitem__(self, key):
        """ Deletes an item from the last dictionary on the stack. """
        del self.stack[-1][key]

    def __contains__(self, key):
        """ True if any dictionary on the stack contains `key`. """
        for d in self.stack:
            if key in d:
                return True
        return False

    def resolve(self, varstring):
        """ Attempts to resolve the object identified by `varstring`.

        If the variable name cannot be resolved an instance of the
        Undefined class is returned in its place.

        """
        obj = self
        for token in varstring.split('.'):
            try:
                obj = obj[token]
            except (TypeError, AttributeError, KeyError, ValueError):
                try:
                    obj = getattr(obj, token)
                except (TypeError, AttributeError):
                    obj = Undefined()
                    break
        return obj

    def push(self, data=None):
        """ Pushes a new data dictionary onto the stack. """
        self.stack.append(data or {})

    def pop(self):
        """ Pops the most recent data dictionary off the stack. """
        self.stack.pop()

    def defined(self, varstring):
        """ Returns true if `varstring` can be successfully resolved. """
        return not isinstance(self.resolve(varstring), Undefined)

    def get(self, key, default=None):
        """ Returns `default` if `key` cannot be found on the stack. """
        for d in reversed(self.stack):
            if key in d:
                return d[key]
        return default

    def update(self, data):
        """ Updates the most recent dictionary on the data stack. """
        self.stack[-1].update(data)


class Lexer:

    """ Transforms an input string into a sequence of tokens. """

    token = collections.namedtuple('Token', 'type tag content')

    def __init__(self, string):
        self.string = string
        self.regex = re.compile(r'(%s.*?%s|%s.*?%s|%s.*?%s|%s.*?%s)' % (
            re.escape(config.delimiters['syntax_start']),
            re.escape(config.delimiters['syntax_end']),
            re.escape(config.delimiters['eprint_start']),
            re.escape(config.delimiters['eprint_end']),
            re.escape(config.delimiters['print_start']),
            re.escape(config.delimiters['print_end']),
            re.escape(config.delimiters['comment_start']),
            re.escape(config.delimiters['comment_end']),
        ), re.DOTALL)

    def __iter__(self):
        for fragment in self.regex.split(self.string):
            if fragment:
                token = self._get_token(fragment)
                if token.content:
                    yield token

    def _get_token(self, fragment):
        if fragment.startswith(config.delimiters['eprint_start']):
            content = self._strip(fragment, 'eprint_start', 'eprint_end')
            type = 'eprint'
            tag = None

        elif fragment.startswith(config.delimiters['print_start']):
            content = self._strip(fragment, 'print_start', 'print_end')
            type = 'print'
            tag = None

        elif fragment.startswith(config.delimiters['syntax_start']):
            content = self._strip(fragment, 'syntax_start', 'syntax_end')
            type = 'syntax'
            tag = content.split(' ')[0]

        elif fragment.startswith(config.delimiters['comment_start']):
            content = None
            type = 'comment'
            tag = None

        else:
            content = fragment
            type = 'text'
            tag = None

        return self.token(type, tag, content)

    def _strip(self, fragment, start, end):
        len_start = len(config.delimiters[start])
        len_end = len(config.delimiters[end])
        return fragment[len_start:-len_end].strip()
