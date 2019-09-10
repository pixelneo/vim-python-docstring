# --------------------------------------------------------------------------
# Ibis: a lightweight template engine.
#
# How it works: A lexer transforms a template string into an iterable
# sequence of tokens. A parser takes this sequence and compiles it into a
# tree of nodes. Each node has a .render() method which takes a context
# object and returns a string. The entire compiled node tree can be rendered
# by calling .render() on the root node.
#
# Compiling and rendering the node tree are two distinct processes. Once
# the template has been compiled it can be cached and rendered multiple times
# with different context objects.
#
# The Template class acts as the public interface to the template engine.
# This is the only class the end-user needs to interact with directly.
#
# A Template object is initialized with a template string. It compiles the
# string and stores the resulting node tree for future rendering. Calling the
# template object's .render() method with a dictionary of key-value pairs or
# a set of keyword arguments renders the template and returns the result as a
# string.
#
# Example:
#
#     >>> template = Template('{{foo}} and {{bar}}')
#
#     >>> template.render(foo='ham', bar='eggs')
#     'ham and eggs'
#
#     >>> template.render({'foo': 1, 'bar': 2})
#     '1 and 2'
#
# Author: Darren Mulholland <darren@mulholland.xyz>
# License: Public Domain
# --------------------------------------------------------------------------


# Library version number.
__version__ = "1.6.0"


# Import modules to make them available to callers via a simple 'import ibis'
# statement. Otherwise callers would have to 'import.foo' for each
# individual module.
from . import config
from . import filters
from . import nodes
from . import loaders
from . import errors

from .templates import Template
