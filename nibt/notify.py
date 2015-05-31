from pyinotify import EventsCodes, ProcessEvent, ThreadedNotifier, WatchManager
import os
import functools
import logging
import collections
import threading
import time
import queue
import fnmatch

class TargetWatcher(object):
    def __init__(self, configuration, builder):
        self._builder = builder
        self._root = configuration.GetExpandedDir("projects", "root_dir")
        self._batch_timeout = float(
            configuration.Get("file_watcher", "event_batch_timeout_ms")) / 1000
        self._moddef_filename = configuration.Get(
                "general", "module_definition_filename")
        self.wm = WatchManager()
        
        self.target_by_glob = collections.defaultdict(dict)
        self.globs_by_target = {}
        self.watched_module_definitions = collections.defaultdict(dict)

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
                    set(self.watched_module_definitions[conf_dir].values()))
            else:
                #TODO Use efficient search instead of linear scan across dict
                found_targets = {}
                for glob_pattern, targets in self.target_by_glob.items():
                    if fnmatch.fnmatchcase(rel_path, glob_pattern):
                        found_targets.update(targets)
                if found_targets:
                    logging.info("Found targets for '%s': %s",
                                 rel_path, found_targets)
                    modified_targets.update(found_targets.values())
                else:
                    logging.info("No targets for '%s'", rel_path)

        if modified_module_definitions or modified_targets:
            self.ModificationsFound(modified_module_definitions,
                                    modified_targets)

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
                    item = self.events_queue.get(
                            block=True,timeout=self._batch_timeout)
                else:
                    item = self.events_queue.get(block=True)
                event_buffer.append(item)
            except queue.Empty as e:
                try:
                    self.ProcessEventsBatch(event_buffer[:])
                except e:
                    logging.exception("Uncaught change event processing error")
                event_buffer = []

    def Join(self):
        self.notifier.stop()

    def ProcessEvent(self, event):
        self.events_queue.put(event)
    
    def _RefreshGlobs(self, target):
        watched_globs = self._builder.GetWatchableSources(target.GetName())
        target_dir = os.path.dirname(target.GetName())
        rel_globs = [os.path.join(target_dir, glob_p)
                     for glob_p in watched_globs]
        logging.info("Watchable sources for %s: %s", target, rel_globs)
        for targets_glob in self.globs_by_target.get(
                target.GetName(),[]):
            del self.target_by_glob[targets_glob][target.GetName()]
        self.globs_by_target[target.GetName()] = rel_globs
        for rel_glob in rel_globs:
            self.target_by_glob[rel_glob][target.GetName()] = target
    
    def ReloadTarget(self, target):
        self._RefreshGlobs(target)

    def AddTarget(self, target): 
        self._RefreshGlobs(target)
        for prefix in self._GetAllModuleDefinitionsForTarget(target.GetName()):
            self.watched_module_definitions[prefix][target.GetName()]=target

    def RemoveTarget(self, target):
        del self.watched[target.GetName()]
        for prefix in self._GetAllModuleDefinitionsForTarget(target.GetName()):
            del self.watched_module_definitions[prefix][target.GetName()]

