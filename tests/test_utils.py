import os

from contextlib import contextmanager


@contextmanager
def temp_file(filename, contents):
    f = open(filename, 'w')
    f.write(contents)
    name = f.name
    f.close()
    try:
        yield name
    finally:
        if os.path.exists(filename):
            os.remove(filename)
