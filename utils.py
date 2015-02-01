import subprocess
import os
import logging
import time

def RunProcess(args):
    start = time.time()
    logging.info("Running %s", args)
    process = subprocess.Popen(
            args, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    out, err = process.communicate()
    if out:
        logging.info("Output '%s'", out.decode())
    if err:
        logging.info("Error '%s'", err.decode())
    result = process.wait()
    logging.info("Result %s, execution time %.3f s.", result, time.time()-start)
    return result, out, err

class FuncCall(object):
    def __init__(self, func, args, kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def __repr__(self):
        func_name = self.func.__qualname__
        args_str = ", ".join([("%r" % (i,)) for i in self.args])
        kwargs_str = ", ".join([("%s=%r" % i) for i in self.kwargs.items()])
        all_args = args_str if not kwargs_str else args_str+", "+kwargs_str
        return "%s(%s)" % (func_name, all_args)

def memoize(log=False):
    cache = {}
    def memoize_callable(func):
        def wrapper(*args, **kwargs):
            args_tp = tuple(args)
            kwargs_tp = tuple(sorted(kwargs.items()))
            tp = (args_tp, kwargs_tp)
            if tp in cache:
                if log:
                    logging.info("Getting value of %s from cache", 
                            FuncCall(func, args, kwargs))
                return cache[tp]
            else:
                if log:
                    logging.info("Calling %s, not cached yet",
                            FuncCall(func, args, kwargs))
                result = func(*args, **kwargs)
                cache[tp] = result
                return result
        return wrapper
    return memoize_callable
