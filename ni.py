#!/usr/bin/python

import functools

import config
import build
import notify
import manager
import graph

class App(object):

    def __init__(self):
        
        self.graph = graph.DependencyTracker(
                lambda deps: self.manager.GetDependencies(deps))
        
        self.build_tracker = build.BuildTracker(self.graph)
        
        self.target_watcher = notify.TargetWatcher()
        
        self.config_evaluator = config.Evaluator()

        self.manager = manager.Manager(
                self.graph,
                self.target_watcher,
                self.build_tracker,
                self.config_evaluator)
        
        # Post init
        self.graph.AddTrackedHandler(
                functools.partial(manager.Manager.OnTracked, self.manager))
        self.graph.AddUntrackedHandler(
                functools.partial(manager.Manager.OnUntracked, self.manager))
        self.graph.AddRefreshingHandler(
                functools.partial(manager.Manager.OnRefreshedAsDependency, self.manager))
        
        self.target_watcher.AddModificationHandler(
                functools.partial(manager.Manager.OnModifiedFiles, self.manager))
    
    def Run(self):
        self.manager.AddActiveTarget("mathapp/main")
        self.manager.Join()

app = App()
app.Run()
