import subprocess
import os
import logging

def RunProcess(args):
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
    logging.info("Result %s", result)
    return result, out, err

def memoize(log=False):
    cache = {}
    def memoize_callable(func):
        def wrapper(*args, **kwargs):
            args_tp = tuple(*args)
            kwargs_tp = tuple(sorted(kwargs.items()))
            tp = (args_tp, kwargs_tp)
            if tp in cache:
                if log:
                    logging.info("Getting value of %s%s, kwargs=%s from cache", 
                            func, args_tp, kwargs)
                return cache[tp]
            else:
                if log:
                    logging.info("Calling %s%s, kwargs=%s, not cached yet",
                            func, args_tp, kwargs)
                result = func(*args, **kwargs)
                cache[tp] = result
                return result
        return wrapper
    return memoize_callable
