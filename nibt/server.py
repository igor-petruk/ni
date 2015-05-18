import functools
import logging

from pkg_resources import resource_stream

from nibt import config, thread_pools, pkg_config, graph, web
from nibt import compile_db, build, notify, moduledef, manager, cpp, dbusinterface

class Server(object):

    def __init__(self):
        LOGGING_FORMAT = "[%(filename)s:%(lineno)s] %(message)s"
        logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)
        
        default_config = resource_stream(__name__, "default_settings.ini")
        
        self.configuration = config.Configuration(
                ["~/.config/ni/settings.ini", default_config])
        
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
        
        self.cpp_plugin = cpp.CppPlugin(
                self.compilation_database, self.pkg_config, self.threading_manager, self.configuration)
        self.cpp_plugin.RegisterBuilders(self.builder)

        self.module_definition_evaluator = moduledef.Evaluator(
                self.cpp_plugin.GetTargets(),
                self.configuration)

        self.manager = manager.Manager(
                self.configuration,
                self.graph,
                self.target_watcher,
                self.build_tracker,
                self.module_definition_evaluator)
        
        self.dbus_interface = dbusinterface.DBusInterface(
                self.configuration, self.manager, self.threading_manager)
        
        self.tracked_target_state_emitter = web.TrackedTargetsStateEmitter(self.graph)
        self.build_progress_state_emitter = web.BuildProcessStateEmitter(self.builder)

        self.web = web.WebUIServer([self.tracked_target_state_emitter, self.build_progress_state_emitter])

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
        self.web.Start()
        self.dbus_interface.Run()
        logging.info("Interrupted, shutting down...")
        self.threading_manager.Join()
        self.target_watcher.Join()

def Main():
    s = Server()
    s.Run()
