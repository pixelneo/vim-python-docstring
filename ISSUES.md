# Not working

## Detection of catching some exceptions

Docstring for this method will contain 'Raises Exception':

~~~{python}
def foo():
  try:
    raise Exception
  except Exception as e:
    pass
~~~

I might try to fix this later. It is necessary to check that `Exception` will not be raised in the `except` block.

## Parsing objects with unaligned multiline comments

There might be a problem when a class of method which contains an unaligned multiline comment or string.

~~~{python}
def foo():
  x=1
"""
Comment
"""
  x=2
  return x
~~~

This will probably result in an error, though the code is valid.
