# --------------------------------------------------------------------------
# Default node classes and associated helpers. Additional node classes can
# be registered using the `@register` decorator:
#
#     @ibis.nodes.register('tag')
#
# Node classes can be given block scope by specifying the required end tag:
#
#     @ibis.nodes.register('tag', 'endtag')
# --------------------------------------------------------------------------

import ast
import operator
import re
import itertools
import collections

from . import config
from . import utils
from . import filters

from .errors import (
    TemplateSyntaxError,
    InvalidFilter,
    FilterError,
    CallError,
    UnpackingError,
)


# Dictionary of registered node classes.
nodemap = { 'endtags': [] }


def register(tag, end_tag=None):

    """ Decorator function for registering node classes. """

    def register_node_class(node_class):
        node_class.end_tag = end_tag
        nodemap[tag] = node_class
        if end_tag:
            nodemap['endtags'].append(end_tag)
        return node_class

    return register_node_class


class Expression:

    """ Helper class for evaluating expression strings.

    An Expression object is initialized with an expression string
    parsed from a template. An expression string can contain a variable
    name or a Python literal, optionally followed by a sequence of filters.

    The Expression object handles the rather convoluted process of parsing
    the string, evaluating the literal or resolving the variable, calling
    the variable if it resolves to a callable, and applying the filters to
    the resulting object. The consumer simply needs to call the expression's
    .eval() method and supply an appropriate Context object.

    Examples of valid expression syntax include:

        foo.bar.baz|default:'bam'|escape
        'foo', 'bar', 'baz'|random

    Arguments can be passed to callables using colon or bracket syntax:

        foo.bar.baz:'bam'|filter:25:'text'
        foo.bar.baz('bam')|filter(25, 'text')

    """

    re_callable = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_.]*)[(](.*)[)]$')

    def __init__(self, expr):
        self.expr = expr.strip()
        self.filters = []
        elements = utils.splitc(expr, '|', strip=True)
        self._parse_expression(elements[0])
        self._parse_filters(elements[1:])
        if self.is_literal:
            self.literal = self._apply_filters(self.literal)

    def eval(self, context):
        if self.is_literal:
            return self.literal
        else:
            return self._resolve_variable(context)

    def _parse_expression(self, expr):
        try:
            self.literal = ast.literal_eval(expr)
            self.is_literal = True
        except:
            self.varstr, self.varargs = self._parse_callable(expr)
            self.is_literal = False

    def _resolve_variable(self, context):
        obj = context.resolve(self.varstr)
        if callable(obj):
            try:
                obj = obj(*self.varargs)
            except:
                raise CallError("error calling [%s]" % self.varstr)
        return self._apply_filters(obj)

    def _parse_callable(self, callable):
        match = self.re_callable.match(callable)
        if match:
            name = match.group(1)
            args = utils.splitc(match.group(2), ',', True, True)
        else:
            elements = utils.splitc(callable, ':', True)
            name = elements[0]
            args = elements[1:]

        for index, arg in enumerate(args):
            try:
                args[index] = ast.literal_eval(arg)
            except:
                msg = "unparsable argument: [%s] in [%s]" % (arg, self.expr)
                raise TemplateSyntaxError(msg) from None

        return name, args

    def _parse_filters(self, filterlist):
        for filter in filterlist:
            name, args = self._parse_callable(filter)
            if name in filters.filtermap:
                self.filters.append((name, filters.filtermap[name], args))
            else:
                msg = "[%s] is not a recognised filter"
                raise InvalidFilter(msg % name)

    def _apply_filters(self, obj):
        for name, func, args in self.filters:
            try:
                obj = func(obj, *args)
            except:
                msg = "error applying filter [%s] in [%s]"
                raise FilterError(msg % (name, self.expr))
        return obj


@register('node')
class Node:

    """ Base class for all node objects. """

    def __init__(self, token=None, children=None):
        self.token = token
        self.children = children or []
        self.process_token(token)

    def __iter__(self):
        for child in self.children:
            yield child

    def __repr__(self):
        return self.repr()

    def render(self, context):
        """ Render the node as a string. """
        return ''.join(child.render(context) for child in self.children)

    def process_token(self, token):
        """ Subclasses can override this method to process token content
        for arguments, etc. """
        pass

    def exit_scope(self):
        """ Subclasses can override this method to process the content of
        block-scoped nodes. """
        pass

    def split_children(self, delimiter_class):
        """ Splits child nodes on the first instance of a delimiter class. """
        for index, child in enumerate(self):
            if isinstance(child, delimiter_class):
                return self.children[:index], child, self.children[index+1:]
        return self.children, None, []

    def repr(self, depth=0):
        """ Basic tree-printing capability for debugging. """
        output = '·  ' * depth + '<%s>\n' % self.__class__.__name__
        for child in self.children:
            output += child.repr(depth + 1)
        return output


@register('root')
class RootNode(Node):
    """ Root node of a template tree. """
    pass


@register('text')
class TextNode(Node):

    """ Plain text. """

    def render(self, context):
        return self.token.content


@register('print')
class PrintNode(Node):

    """ Evaluates an expression and prints its result.

        {{ <expr> }}

    Multiple expressions can be listed separated by 'or' or '||'.
    The first expression to resolve to a truthy value will be
    printed. (If none of the expressions are truthy the final value
    will be printed regardless.)

        {{ <expr> or <expr> or <expr> }}

    Alternatively, print statements can use the ternary operator: ?? ::

        {{ <test-expr> ?? <expr1> :: <expr2> }}

    If <test-expr> is truthy, <expr1> will be printed, otherwise <expr2>
    will be printed.

    Note that *either* 'or'-chaining or the ternary operator can be used
    in a single print statement, but not both.

    """

    escape = False

    def process_token(self, token):

        # Check for a ternary operator.
        chunks = utils.splitre(token.content, (r'\?\?', r'\:\:'), True)
        if len(chunks) == 5 and chunks[1] == '??' and chunks[3] == '::':
            self.is_ternary = True
            self.testexpr = Expression(chunks[0])
            self.iftrue = Expression(chunks[2])
            self.iffalse = Expression(chunks[4])

        # Look for a list of 'or' separated expressions.
        else:
            self.is_ternary = False
            exprs = utils.splitre(token.content, (r'\s+or\s+', r'\|\|'))
            self.exprs = [Expression(e) for e in exprs]

    def render(self, context):
        if self.is_ternary:
            if self.testexpr.eval(context):
                content = self.iftrue.eval(context)
            else:
                content = self.iffalse.eval(context)
        else:
            for expr in self.exprs:
                content = expr.eval(context)
                if content:
                    break

        if self.escape:
            return filters.filtermap['escape'](str(content))
        else:
            return str(content)


@register('eprint')
class EscapedPrintNode(PrintNode):
    """ Print node with automatic escaping. """
    escape = True


@register('for', 'endfor')
class ForNode(Node):

    """ Implements for/empty looping over an iterable expression.

        {% for <var> in <expr> %} ... [ {% empty %} ... ] {% endfor %}

    Supports unpacking into multiple loop variables:

        {% for <var1>, <var2> in <expr> %}

    """

    regex = re.compile(r'for\s+(\w+(?:,\s*\w+)*)\s+in\s+(.+)')

    def process_token(self, token):
        match = self.regex.match(token.content)
        if match is None:
            msg = "malformed [for] tag: [%s]" % token.content
            raise TemplateSyntaxError(msg)
        self.loopvars = [var.strip() for var in match.group(1).split(',')]
        self.expr = Expression(match.group(2))

    def render(self, context):
        items = self.expr.eval(context)
        if items and hasattr(items, '__iter__'):
            items = list(items)
            length = len(items)
            unpack = len(self.loopvars) > 1
            output = []
            for index, item in enumerate(items):
                context.push()
                if unpack:
                    try:
                        unpacked = dict(zip(self.loopvars, item))
                    except TypeError:
                        msg = 'cannot unpack [%s] in [%s]' % (
                            repr(item), self.token.content
                        )
                        raise UnpackingError(msg)
                    else:
                        context.update(unpacked)
                else:
                    context[self.loopvars[0]] = item
                context['loop'] = {
                    'index': index,
                    'count': index + 1,
                    'length': length,
                    'is_first': index == 0,
                    'first':    index == 0,             # deprecated - will be removed
                    'is_last': index == length - 1,
                    'last':    index == length - 1,     # deprecated - will be removed
                    'parent': context.get('loop'),
                }
                output.append(self.for_branch.render(context))
                context.pop()
            return ''.join(output)
        else:
            return self.empty_branch.render(context)

    def exit_scope(self):
        fornodes, emptynode, emptynodes = self.split_children(EmptyNode)
        self.for_branch = Node(None, fornodes)
        self.empty_branch = Node(None, emptynodes)


@register('empty')
class EmptyNode(Node):
    """ Delimiter node to implement for/empty branching. """
    pass


@register('if', 'endif')
class IfNode(Node):

    """ Implements if/elif/else branching.

        {% if [not] <expr> %} ... {% endif %}
        {% if [not] <expr> <operator> <expr> %} ... {% endif %}
        {% if <...> %} ... {% elif <...> %} ... {% else %} ... {% endif %}

    Supports 'and' and 'or' conjunctions; 'and' has higher precedence so:

        if a and b or c and d

    is treated as:

        if (a and b) or (c and d)

    Note that explicit brackets are not supported.

    """

    condition = collections.namedtuple('Condition', 'negated lhs op rhs')

    re_condition = re.compile(r'''
        (not\s+)?(.+?)\s+(==|!=|<|>|<=|>=|not[ ]in|in)\s+(.+)
        |
        (not\s+)?(.+)
        ''', re.VERBOSE
    )

    operators = {
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '>': operator.gt,
        '<=': operator.le,
        '>=': operator.ge,
        'in': lambda a, b: a in b,
        'not in': lambda a, b: a not in b,
    }

    def process_token(self, token):
        try:
            tag, conditions = token.content.split(None, 1)
        except ValueError:
            msg = "malformed [%s] tag: [%s]" % (token.tag, token.content)
            raise TemplateSyntaxError(msg) from None

        self.condition_groups = [
            [
                self.parse_condition(condstr)
                for condstr in utils.splitre(or_block, (r'\s+and\s+', r'&&'))
            ]
            for or_block in utils.splitre(conditions, (r'\s+or\s+', r'\|\|'))
        ]

    def parse_condition(self, condstr):
        match = self.re_condition.match(condstr)
        if match.group(2):
            return self.condition(
                negated = bool(match.group(1)),
                lhs = Expression(match.group(2)),
                op = self.operators[match.group(3)],
                rhs = Expression(match.group(4)),
            )
        else:
            return self.condition(
                negated = bool(match.group(5)),
                lhs = Expression(match.group(6)),
                op = None,
                rhs = None,
            )

    def eval_condition(self, cond, context):
        try:
            if cond.op:
                result = cond.op(cond.lhs.eval(context), cond.rhs.eval(context))
            else:
                result = operator.truth(cond.lhs.eval(context))
        except:
            # We treat an exception during evaluation as a false result.
            # We should probably raise an exception of our own here instead.
            result = False
        if cond.negated:
            result = not result
        return result

    def render(self, context):
        for condition_group in self.condition_groups:
            for condition in condition_group:
                is_true = self.eval_condition(condition, context)
                if not is_true:
                    break
            if is_true:
                break
        if is_true:
            return self.true_branch.render(context)
        else:
            return self.false_branch.render(context)

    def exit_scope(self):
        ifnodes, elifnode, elifnodes = self.split_children(ElifNode)
        if elifnode:
            self.true_branch = Node(None, ifnodes)
            self.false_branch = IfNode(elifnode.token, elifnodes)
            self.false_branch.exit_scope()
            return
        ifnodes, elsenode, elsenodes = self.split_children(ElseNode)
        self.true_branch = Node(None, ifnodes)
        self.false_branch = Node(None, elsenodes)


@register('elif')
class ElifNode(Node):
    """ Delimiter node to implement if/elif branching. """
    pass


@register('else')
class ElseNode(Node):
    """ Delimiter node to implement if/else branching. """
    pass


@register('cycle')
class CycleNode(Node):

    """ Cycles over an iterable expression.

        {% cycle <expr> %}

    Each time the node is evaluated it will render the next value in the
    sequence, looping once it reaches the end; e.g.

        {% cycle 'odd', 'even' %}

    will alternate continuously between printing 'odd' and 'even'.

    """

    def process_token(self, token):
        try:
            tag, arg = token.content.split(None, 1)
        except ValueError:
            msg = "malformed [cycle] tag: [%s]" % token.content
            raise TemplateSyntaxError(msg) from None
        self.expr = Expression(arg)

    def render(self, context):
        # We store our state info on the context object to avoid a threading
        # mess if the template is being simultaneously rendered by multiple
        # threads.
        if not self in context.stash:
            items = self.expr.eval(context)
            if not hasattr(items, '__iter__'):
                items = ''
            context.stash[self] = itertools.cycle(items)
        iterator = context.stash[self]
        return str(next(iterator, ''))


@register('include')
class IncludeNode(Node):

    """ Includes a sub-template.

        {% include <expr> %}

    Requires a template ID which can be supplied as either a string literal
    or a variable resolving to a string. This ID will be passed to the
    registered template loader.

    """

    def process_token(self, token):
        try:
            tag, arg = token.content.split(None, 1)
        except ValueError:
            msg = "malformed [include] tag: [%s]" % token.content
            raise TemplateSyntaxError(msg) from None

        expr = Expression(arg)

        if expr.is_literal:
            template = config.loader(expr.literal)
            self.children.append(template.root)
        else:
            self.expr = expr

    def render(self, context):
        if self.children:
            return ''.join(child.render(context) for child in self)
        else:
            template_id = self.expr.eval(context)
            template = config.loader(template_id)
            return template.root.render(context)


@register('extends')
class ExtendsNode(Node):

    """ Specifies a parent template.

    Indicates that the current template inherits from or 'extends' the
    specified parent template.

        {% extends "parent.txt" %}

    Requires a template ID to pass to the registered template loader.
    This must be supplied as a string literal (not a variable)
    as the parent template must be loaded at compile-time.

    """

    def process_token(self, token):
        try:
            tag, arg = token.content.split(None, 1)
        except ValueError:
            msg = "malformed [extends] tag: [%s]" % token.content
            raise TemplateSyntaxError(msg) from None

        expr = Expression(arg)

        if expr.is_literal:
            template = config.loader(expr.literal)
            self.children.append(template.root)
        else:
            msg = "malformed [extends] tag: [%s]" % token.content
            raise TemplateSyntaxError(msg) from None


@register('block', 'endblock')
class BlockNode(Node):

    """ Implements template inheritance.

        {% block title %} ... {% endblock %}

    A block tag defines a titled block of content that can be overridden
    by similarly titled blocks in child templates.

    """

    def process_token(self, token):
        self.title = token.content[5:].strip()

    def render(self, context):
        # We only want to render the first block of any given title
        # that we encounter in the node tree, although we want to substitute
        # the content of the last block of that title in its place.
        block_list = context.template.registry[self.title]
        if block_list[0] is self:
            return self.render_block(context, block_list[:])
        else:
            return ''

    def render_block(self, context, block_list):
        # A call to {{ super }} inside a block renders and returns the
        # content of the block's immediate ancestor. That ancestor may
        # itself contain a {{ super }} call, so we start at the end of the
        # list and recursively work our way backwards, popping off nodes
        # as we go.
        if block_list:
            last_block = block_list.pop()
            context.push()
            context['super'] = lambda: self.render_block(context, block_list)
            output = ''.join(child.render(context) for child in last_block)
            context.pop()
            return output
        else:
            return ''


@register('spaceless', 'endspaceless')
class SpacelessNode(Node):

    """ Strips all whitespace between HTML tags.

        {% spaceless %} ... {% endspaceless %}

    """

    def render(self, context):
        output = ''.join(child.render(context) for child in self)
        return filters.filtermap['spaceless'](output).strip()


@register('trim', 'endtrim')
class TrimNode(Node):

    """ Trims leading and trailing whitespace.

        {% trim %} ... {% endtrim %}

    """

    def render(self, context):
        return ''.join(child.render(context) for child in self).strip()


@register('with', 'endwith')
class WithNode(Node):

    """ Caches a complex expression under a simpler alias.

        {% with <alias> = <expr> %} ... {% endwith %}

    """

    def process_token(self, token):
        try:
            alias, expr = token.content[4:].split('=', 1)
        except ValueError:
            msg = "malformed [with] tag: [%s]" % token.content
            raise TemplateSyntaxError(msg) from None
        self.alias = alias.strip()
        self.expr = Expression(expr.strip())

    def render(self, context):
        context.push()
        context[self.alias] = self.expr.eval(context)
        rendered = ''.join(child.render(context) for child in self)
        context.pop()
        return rendered
