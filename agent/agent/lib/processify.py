#pylint: disable=C0103,W0703,W0105
'''
Copyright 2014 eBay Software Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
""" processify annotation"""
import os
import sys
import traceback
from functools import wraps
from multiprocessing import Process, Queue


def processify(func):
    '''Decorator to run a function as a process.

    Be sure that every argument and the return value
    is *pickable*.

    The created process is joined, so the code does not
    run in parallel.

    '''

    def process_func(q, *args, **kwargs):
        """ process func """
        try:
            ret = func(*args, **kwargs)
        except Exception:
            ex_type, ex_value, tb = sys.exc_info()
            error = ex_type, ex_value, ''.join(traceback.format_tb(tb))
            ret = None
        else:
            error = None

        q.put((ret, error))

    # register original function with different name
    # in sys.modules so it is pickable
    process_func.__name__ = func.__name__ + 'processify_func'
    setattr(sys.modules[__name__], process_func.__name__, process_func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        """ wrapper """
        q = Queue()
        p = Process(target=process_func, args=[q] + list(args), kwargs=kwargs)
        p.start()
        p.join()
        ret, error = q.get()

        if error:
            ex_type, ex_value, tb_str = error
            message = '%s (in subprocess)\n%s' % (ex_value, tb_str)
            raise ex_type(message)

        return ret
    return wrapper


@processify
def test_function():
    """ test """
    return os.getpid()


@processify
def test_exception():
    """ test """
    raise RuntimeError('xyz')


def test():
    """ test """
    print os.getpid()
    print test_function()
    test_exception()

if __name__ == '__main__':
    test()
