from pyinotify import EventsCodes, ProcessEvent, ThreadedNotifier, WatchManager
import os
import functools
import logging
import collections
import threading
import time
import queue

class TargetWatcher(object):
    def __init__(self, configuration):
        self._root = configuration.GetExpandedDir("projects", "root_dir")
        self._batch_timeout = float(
            configuration.Get("file_watcher", "event_batch_timeout_ms")) / 1000
        self._moddef_filename = configuration.Get(
                "general", "module_definition_filename")
        self.wm = WatchManager()
        
        self.watched = {}
        self.watched_module_definitions = collections.defaultdict(set)

        mask = (EventsCodes.ALL_FLAGS['IN_DELETE'] | 
                EventsCodes.ALL_FLAGS['IN_CREATE'] |
                EventsCodes.ALL_FLAGS['IN_MODIFY'] )
        handler = functools.partial(TargetWatcher.ProcessEvent, self)
        
        self.events_queue = queue.Queue()

        self.acc_thread = threading.Thread(target=functools.partial(
            TargetWatcher.AccumulationThreadProc, self), daemon=True)
        self.acc_thread.start()
        
        self.notifier = ThreadedNotifier(self.wm, handler)
        self.notifier.start()
        self.watch = self.wm.add_watch(
                self._root, mask, rec=True, auto_add=True)
        self.modification_handlers = []
    
    def _GetAllModuleDefinitionsForTarget(self, target_name):
        prefix = ""
        module_definition_dirs = [""]
        for path_element in target_name.split("/"):
            if prefix:
                prefix = prefix + "/" + path_element
            else:
                prefix = path_element
            module_definition_dirs.append(prefix)
        return module_definition_dirs

    def AddModificationHandler(self, handler):
        self.modification_handlers.append(handler)

    def ProcessEventsBatch(self, batch):
        modified_targets = set()
        modified_module_definitions = set()
        root_prefix_len = len(self._root)
        for event in batch:
            rel_path = event.pathname[root_prefix_len+1:]
            if rel_path.endswith(self._moddef_filename):
                conf_dir = rel_path[:-len(self._moddef_filename)-1]
                modified_module_definitions.update(
                        self.watched_module_definitions[conf_dir])
            else:
                #TODO Use efficient search instead of linear scan across dict
                for watched_key, watched_target in self.watched.items():
                    if rel_path.startswith(watched_key):
                        modified_targets.add(watched_target)
                        break
                
        if modified_module_definitions or modified_targets:
            self.ModificationsFound(modified_module_definitions, modified_targets)

    def ModificationsFound(self, modified_module_definitions, modified_targets):
        logging.info("Files modified: module definitions %s, other %s",
                modified_module_definitions, modified_targets)
        for handler in self.modification_handlers:
            handler(modified_module_definitions, modified_targets)

    def AccumulationThreadProc(self):
        event_buffer = []
        while True:
            try:
                if event_buffer:
                    item = self.events_queue.get(block=True,timeout=self._batch_timeout)
                else:
                    item = self.events_queue.get(block=True)
                event_buffer.append(item)
            except queue.Empty as e:
                self.ProcessEventsBatch(event_buffer[:])
                event_buffer = []

    def Join(self):
        self.notifier.stop()

    def ProcessEvent(self, event):
        self.events_queue.put(event)

    def AddTarget(self, target):
        self.watched[target.GetName()] = target
        for prefix in self._GetAllModuleDefinitionsForTarget(target.GetName()):
            self.watched_module_definitions[prefix].add(target)
        logging.info("watched %s %s", self.watched, self.watched_module_definitions)

    def RemoveTarget(self, target):
        del self.watched[target.GetName()]
        for prefix in self._GetAllModuleDefinitionsForTarget(target.GetName()):
            self.watched_module_definitions[prefix].remove(target)

