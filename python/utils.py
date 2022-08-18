def concat_(*args):
    """Converts `args` into string and joines them"""
    return "".join([str(x) for x in list(args)])
