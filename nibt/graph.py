import logging
import functools

class DependencyTracker(object):

    def __init__(self, get_dependencies):
        self._get_dependencies = get_dependencies
        self._provides = {}
        self._depends = {}
        self._active_targets = set()

        default_tracking = functools.partial(
                DependencyTracker._LogEvent, self, "Tracking %s")
        default_untracking = functools.partial(
                DependencyTracker._LogEvent, self, "Untracking %s")
        default_refreshing = functools.partial(
                DependencyTracker._LogEvent, self, "Refreshing %s")

        self._on_tracked_handlers = set([default_tracking])
        self._on_untracked_handlers = set([default_untracking])
        self._on_refreshed_handlers = set([default_refreshing])
    
    def GetDependencies(self, target_name):
        return self._depends[target_name]
    
    def GetAllDependencies(self):
        return self._depends

    def _LogEvent(self, message, item):
        logging.info(message, item)

    def _Notify(self, handlers, item):
        for handler in handlers:
            handler(item)

    def _AddTarget(self, target):
        if target not in self._depends:
            dependencies = self._get_dependencies(target)
            self._depends[target] = dependencies
            for dependency in dependencies:
                if dependency not in self._provides:
                    self._provides[dependency] = set([target])
                else:
                    self._provides[dependency].add(target)
                self._AddTarget(dependency)
            self._items_added.add(target)

    def _RemoveTarget(self, target):
        if target not in self._active_targets and target not in self._provides:
            if target in self._depends:
                dependencies = self._depends[target]
                del self._depends[target] 
                for dependency in dependencies:
                    self._provides[dependency].remove(target)
                    if not self._provides[dependency]:
                        del self._provides[dependency]
                    self._RemoveTarget(dependency)
                self._items_removed.add(target)
    
    def _DumpState(self):
        logging.info("Active: %s", self._active_targets)
        logging.info("Depends: %s", self._depends)
        logging.info("Provides: %s", self._provides)

    def AddTrackedHandler(self, handler):
        self._on_tracked_handlers.add(handler)

    def AddUntrackedHandler(self, handler):
        self._on_untracked_handlers.add(handler)
    
    def AddRefreshingHandler(self, handler):
        self._on_refreshed_handlers.add(handler)

    def _StartRecoding(self):
        self._items_added = set()
        self._items_removed = set()
   
    def _GetEligibleForRefreshItems(self, dependency_target):
        refresh_set = set([dependency_target])
        for provide_targets in self._provides.get(dependency_target, set()):
            refresh_set.update(self._GetEligibleForRefreshItems(provide_targets))
        return refresh_set

    def _NotifyOnChanges(self):
        final_items_added = self._items_added - self._items_removed
        final_items_removed = self._items_removed - self._items_added
        for item_added in final_items_added:
            self._Notify(self._on_tracked_handlers, item_added)
        for item_removed in final_items_removed:
            self._Notify(self._on_untracked_handlers, item_removed)
        return final_items_added, final_items_removed

    def AddTopLevelTarget(self, target):
        self._StartRecoding()
        logging.info("Adding top level target %s", target)
        if target not in self._active_targets:
            self._active_targets.add(target)
            self._AddTarget(target)
        self._DumpState()
        return self._NotifyOnChanges()

    def RemoveTopLevelTarget(self, target):
        self._StartRecoding()
        logging.info("Removing top level target %s", target)
        if target in self._active_targets:
            self._active_targets.remove(target)
            self._RemoveTarget(target)
        self._DumpState()
        return self._NotifyOnChanges()

    def RefreshTarget(self, target):
        self._StartRecoding()
        logging.info("Refreshing target %s", target)
        dependencies = self._depends[target]
        for dependency in dependencies:
            self._provides[dependency].remove(target)
            if not self._provides[dependency]:
                del self._provides[dependency]
            self._RemoveTarget(dependency)
        del self._depends[target]
        self._items_removed.add(target)
        self._AddTarget(target)
        self._DumpState()
        added, removed = self._NotifyOnChanges()
        refreshed = self._GetEligibleForRefreshItems(target)
        for refreshed_item in refreshed:
            self._Notify(self._on_refreshed_handlers, refreshed_item)
        return added, removed, refreshed
    


