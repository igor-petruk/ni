import os

import common
import config
import graph
import logging
import functools
import notify
import build
import time

class Manager(object):
    def __init__(self):
        self.active_targets = set()
        
        self.graph = graph.DependencyTracker(functools.partial(Manager.GetDependencies, self))
        self.graph.AddTrackedHandler(functools.partial(Manager.OnTracked, self))
        self.graph.AddUntrackedHandler(functools.partial(Manager.OnUntracked, self))
        self.graph.AddRefreshingHandler(functools.partial(Manager.OnRefreshedAsDependency, self))
        
        self.tracker = notify.TargetWatcher()
        self.tracker.AddModificationHandler(functools.partial(Manager.OnModifiedFiles, self))
    
        self.build_tracker = build.BuildTracker(self.graph)

    def Join(self):
        self.tracker.Join()

    def GetDependencies(self, dep):
        target = self._LoadTarget(dep)
        return set(target.GetConfig().deps)

    def AddActiveTarget(self, target_name):
        if target_name not in self.active_targets:
            self.active_targets.add(target_name)
            self.graph.AddTopLevelTarget(target_name)
            self.build_tracker.Build()

    def _AddTarget(self, target_name):
        target = self._LoadTarget(target_name)
        self.build_tracker.AddTarget(target)
        return target

    def _RemoveTarget(self, target_name):
        self.build_tracker.RemoveTarget(target_name)

    def OnTracked(self, target_name):
        logging.info("Manager tracking %s", target_name)
        self._AddTarget(target_name)
        self.tracker.AddTarget(self.build_tracker.GetTarget(target_name))

    def OnUntracked(self, target_name):
        logging.info("Manager untracking %s", target_name)
        self.tracker.RemoveTarget(self.build_tracker.GetTarget(target_name))
        self._RemoveTarget(target_name)

    def OnRefreshedAsDependency(self, target_name):
        target = self._LoadTarget(target_name)
        self.build_tracker.ReloadTarget(target)
        logging.info("Manager refreshing %s", target_name)

    def OnModifiedFiles(self, modified_configs, modified_other_files):
        started_eval = time.time()
        for modified_config in modified_configs:
            self.graph.RefreshTarget(modified_config.GetName())
        for modified_other_files_item in modified_other_files:
            self.graph.RefreshTarget(modified_other_files_item.GetName())
        started_build = time.time()
        logging.info("Changes detection took %.0f ms", (started_build - started_eval)*1000)
        self.build_tracker.Build()
        logging.info("Building changed targets took %.3f sec", time.time() - started_build)

    def _LoadTarget(self, target_name):
        target = common.Target(target_name)
        evaluator = config.Evaluator()
        evaluator.RefreshConfig(target)
        return target

m = Manager()
m.AddActiveTarget("mathapp/main")
m.Join()
