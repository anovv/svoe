def flatten_tuples(data):
    if isinstance(data, tuple):
        if len(data) == 0:
            return ()
        else:
            return flatten_tuples(data[0]) + flatten_tuples(data[1:])
    else:
        return (data,)