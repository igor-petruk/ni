import logging

import concurrent.futures

class ThreadingManager(object):
    def __init__(self, configuration):
        self.configuration = configuration
        self.thread_pools = {}

    def _GetThreadPoolSize(self, name):
        setting_name = name+"_workers"
        return int(self.configuration.Get(
            "thread_pools", setting_name, raise_exception=False,
            default=self.configuration.Get("thread_pools", "default_workers")))

    def GetThreadPool(self, name):
        if name not in self.thread_pools:
            tp_size = self._GetThreadPoolSize(name)
            logging.info("Allocating thread pool '%s' of size %s", name, tp_size)
            tp = concurrent.futures.ThreadPoolExecutor(max_workers=tp_size)
            self.thread_pools[name] = tp
            return tp
        else:
            return self.thread_pools[name]

    def Join(self):
        for tp_name, tp in self.thread_pools.items():
            logging.info("Shutting down thread pool '%s'", tp_name)
            tp.Shutdown()
        
