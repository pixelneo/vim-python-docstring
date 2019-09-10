# --------------------------------------------------------------------------
# Error handlers.
# --------------------------------------------------------------------------


class TemplateError(Exception):
    """ Base class for all exceptions raised by the template engine. """
    pass


class LoadError(TemplateError):
    """ Error attempting to load a template file. """
    pass


class NestingError(TemplateError):
    """ Improperly nested template tags. """
    pass


class InvalidTag(TemplateError):
    """ Unrecognised template tag. """
    pass


class InvalidFilter(TemplateError):
    """ Unrecognised filter name. """
    pass


class TemplateSyntaxError(TemplateError):
    """ Invalid template syntax. """
    pass


class CallError(TemplateError):
    """ Raised if a callable variable throws an exception. """
    pass


class FilterError(TemplateError):
    """ Raised if a filter function throws an exception. """
    pass


class UnpackingError(TemplateError):
    """ Raised if an attempt to unpack a for-loop variable fails. """
    pass


class TemplateNotFound(TemplateError):
    """ Raised if a loader cannot locate a template. """
    pass


class Undefined:

    """ Null type returned when a context lookup fails. """

    def __str__(self):
        return ''

    def __bool__(self):
        return False

    def __len__(self):
        return 0

    def __contains__(self, key):
        return False

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True
