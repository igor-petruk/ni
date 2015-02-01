#!/usr/bin/python

import functools

import config
import build
import notify
import manager
import graph
import compile_db
import cpp
import logging

class App(object):

    def __init__(self):
        LOGGING_FORMAT = "[%(filename)s:%(lineno)s] %(message)s"
        logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)

        self.graph = graph.DependencyTracker(
                lambda deps: self.manager.GetDependencies(deps))
        
        self.compilation_database = compile_db.Database()
        
        self.targets_state = build.TargetsState()

        self.builder = build.Builder(self.targets_state)

        self.build_tracker = build.BuildTracker(
                self.graph, self.targets_state, self.builder,
                self.compilation_database)
        
        self.target_watcher = notify.TargetWatcher()
        
        self.config_evaluator = config.Evaluator()

        self.manager = manager.Manager(
                self.graph,
                self.target_watcher,
                self.build_tracker,
                self.config_evaluator)
        
        self.cpp_lib_builder = cpp.CppStaticLibraryBuilder(self.compilation_database)
        self.cpp_binary_builder = cpp.CppBinaryBuilder(self.compilation_database)

        # Post init
        self.graph.AddTrackedHandler(
                functools.partial(manager.Manager.OnTracked, self.manager))
        self.graph.AddUntrackedHandler(
                functools.partial(manager.Manager.OnUntracked, self.manager))
        self.graph.AddRefreshingHandler(
                functools.partial(manager.Manager.OnRefreshedAsDependency, self.manager))
    

        self.build_tracker.builder.RegisterBuilder(
                "c++/default", self.cpp_lib_builder)
        self.build_tracker.builder.RegisterBuilder(
                "c++/binary", self.cpp_binary_builder)

        self.target_watcher.AddModificationHandler(
                functools.partial(manager.Manager.OnModifiedFiles, self.manager))
    
    def Run(self):
        self.manager.AddActiveTarget("mathapp/main")
        self.manager.Join()

app = App()
app.Run()
