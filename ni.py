#!/usr/bin/python

import functools
import logging

import config
import moduledef
import build
import notify
import manager
import graph
import compile_db
import cpp
import pkg_config
import thread_pools

class App(object):

    def __init__(self):
        LOGGING_FORMAT = "[%(filename)s:%(lineno)s] %(message)s"
        logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)
        
        self.configuration = config.Configuration(
                ["~/.config/ni/settings.ini", "/etc/ni/settings.ini"])
        
        self.threading_manager = thread_pools.ThreadingManager(self.configuration)

        self.pkg_config = pkg_config.PkgConfig()

        self.graph = graph.DependencyTracker(
                lambda deps: self.manager.GetDependencies(deps))
        
        self.compilation_database = compile_db.Database(self.configuration)
        
        self.targets_state = build.TargetsState()

        self.builder = build.Builder(self.configuration, self.targets_state)

        self.build_tracker = build.BuildTracker(
                self.graph, self.targets_state, self.builder,
                self.compilation_database, self.threading_manager)
        
        self.target_watcher = notify.TargetWatcher(self.configuration)
        
        self.module_definition_evaluator = moduledef.Evaluator(self.configuration)

        self.manager = manager.Manager(
                self.configuration,
                self.graph,
                self.target_watcher,
                self.build_tracker,
                self.module_definition_evaluator)
        
        self.cpp_lib_builder = cpp.CppStaticLibraryBuilder(
                self.compilation_database, self.pkg_config, self.threading_manager)
        self.cpp_binary_builder = cpp.CppBinaryBuilder(
                self.compilation_database, self.pkg_config, self.threading_manager)

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
