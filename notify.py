from pyinotify import EventsCodes, ProcessEvent, ThreadedNotifier, WatchManager
import os
import functools
import common
import logging
import collections
import threading
import time
import queue

class TargetWatcher(object):
    def __init__(self):
        self.wm = WatchManager()
        
        self.watched = {}
        self.watched_configs = collections.defaultdict(set)

        mask = (EventsCodes.ALL_FLAGS['IN_DELETE'] | 
                EventsCodes.ALL_FLAGS['IN_CREATE'] |
                EventsCodes.ALL_FLAGS['IN_MODIFY'] )
        handler = functools.partial(TargetWatcher.ProcessEvent, self)
        
        self.events_queue = queue.Queue()

        self.acc_thread = threading.Thread(target=functools.partial(
            TargetWatcher.AccumulationThreadProc, self))
        self.acc_thread.start()

        self.notifier = ThreadedNotifier(self.wm, handler)
        self.notifier.start()
        self.watch = self.wm.add_watch(
                common.GetRootFromEnv(), mask, rec=True, auto_add=True)
        self.modification_handlers = []
    
    def _GetAllConfigsForTarget(self, target_name):
        prefix = ""
        config_dirs = [""]
        for path_element in target_name.split("/"):
            if prefix:
                prefix = prefix + "/" + path_element
            else:
                prefix = path_element
            config_dirs.append(prefix)
        return config_dirs

    def AddModificationHandler(self, handler):
        self.modification_handlers.append(handler)

    def ProcessEventsBatch(self, batch):
        modified_targets = set()
        modified_configs = set()
        root_prefix_len = len(common.GetRootFromEnv())
        for event in batch:
            rel_path = event.pathname[root_prefix_len+1:]
            if rel_path.endswith(common.CONF_NAME):
                conf_dir = rel_path[:-len(common.CONF_NAME)-1]
                modified_configs.update(self.watched_configs[conf_dir])
            else:
                conf_dir = rel_path[:-len(os.path.basename(rel_path))-1]
                if conf_dir in self.watched:
                    modified_targets.add(self.watched[conf_dir])
                
        if modified_configs or modified_targets:
            self.ModificationsFound(modified_configs, modified_targets)

    def ModificationsFound(self, modified_configs, modified_targets):
        logging.info("Files modified: configs %s, other %s",
                modified_configs, modified_targets)
        for handler in self.modification_handlers:
            handler(modified_configs, modified_targets)

    def AccumulationThreadProc(self):
        event_buffer = []
        while True:
            try:
                if event_buffer:
                    item = self.events_queue.get(block=True,timeout=0.3)
                else:
                    item = self.events_queue.get(block=True)
                event_buffer.append(item)
            except queue.Empty as e:
                self.ProcessEventsBatch(event_buffer[:])
                event_buffer = []

    def Join(self):
        self.notifier.join()
        self.acc_thread.join()

    def ProcessEvent(self, event):
        self.events_queue.put(event)

    def AddTarget(self, target):
        self.watched[target.GetName()] = target
        for prefix in self._GetAllConfigsForTarget(target.GetName()):
            self.watched_configs[prefix].add(target)
        logging.info("watched %s %s", self.watched, self.watched_configs)

    def RemoveTarget(self, target):
        del self.watched[target.GetName()]
        for prefix in self._GetAllConfigsForTarget(target.GetName()):
            self.watched_configs[prefix].remove(target)

