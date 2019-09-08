# Not working

## Detection of catching some exceptions

Docstring for this method will conain 'Raises Exception':

~~~{python}
def foo():
  try:
    raise Exception
  except Exception as e:
    pass
~~~

I might try to fix this later. It is necessary to check that `Exception` will not be raised in the `except` block.

