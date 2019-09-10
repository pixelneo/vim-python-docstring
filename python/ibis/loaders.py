# --------------------------------------------------------------------------
# Default template loaders.
# --------------------------------------------------------------------------

import os

from .templates import Template
from .errors import LoadError, TemplateNotFound


class FileLoader:

    """ Loads templates from the file system. Assumes files are utf-8 encoded.

    Compiled templates are cached in memory, so they only need to be
    compiled once. Templates are *not* automatically recompiled if the
    underlying template file changes.

    A FileLoader instance should be initialized with a path to a base
    template directory.

        loader = FileLoader('/path/to/base/directory')

    The loader instance can then be called with one or more path strings.
    The loader will return the template object corresponding to the first
    existing template file or raise a TemplateNotFound exception if no file
    can be located.

    Note that the path strings may include subdirectory paths:

        template = loader('foo.txt')
        template = loader('subdir/foo.txt')

    """

    def __init__(self, root):
        self.root = root
        self.cache = {}

    def __call__(self, *paths):
        for path in paths:

            if path in self.cache:
                return self.cache[path]

            fullpath = os.path.join(self.root, path)
            if os.path.isfile(fullpath):
                try:
                    with open(fullpath, encoding='utf-8') as file:
                        return self.cache.setdefault(path, Template(file.read()))
                except OSError:
                    raise LoadError("error loading template file [%s]" % path)

        raise TemplateNotFound()


class FileReloader:

    """ Loads templates from the file system. Assumes files are utf-8 encoded.

    Compiled templates are cached in memory, so they only need to be
    compiled once. Templates are automatically recompiled if the
    underlying template file changes.

    """

    def __init__(self, root):
        self.root = root
        self.cache = {}

    def __call__(self, *paths):
        for path in paths:

            fullpath = os.path.join(self.root, path)
            if os.path.isfile(fullpath):
                try:
                    mtime = os.path.getmtime(fullpath)
                    if path in self.cache:
                        if mtime == self.cache[path][0]:
                            return self.cache[path][1]
                    with open(fullpath, encoding='utf-8') as file:
                        self.cache[path] = (mtime, Template(file.read()))
                        return self.cache[path][1]
                except OSError:
                    raise LoadError("error loading template file [%s]" % path)

        raise TemplateNotFound()


class DictLoader:

    """ Loads templates from a dictionary of template strings. """

    def __init__(self, strings):
        self.templates = {}
        self.strings = strings

    def __call__(self, *names):
        for name in names:
            if name in self.templates:
                return self.templates[name]
            elif name in self.strings:
                return self.templates.setdefault(name, Template(self.strings[name]))
        raise TemplateNotFound()
