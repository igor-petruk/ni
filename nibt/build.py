import logging
import os
import glob
import subprocess

class BuildingContext(object):
    def __init__(self, targets, build_results, mode):
        self.build_results = build_results
        self.targets = targets
        self.mode = mode


class Builder(object):
    def __init__(self, configuration, targets_state):
        self.targets_state = targets_state
        self.build_results = {}
        self.root = configuration.GetExpandedDir("projects", "root_dir")
        self.builders = {}
        self.build_start_handlers = []
        self.build_finish_handlers = []
    
    def AddBuildStartHandler(self, handler):
        self.build_start_handlers.append(handler)

    def AddBuildFinishHandler(self, handler):
        self.build_finish_handlers.append(handler)

    def RegisterBuilder(self, mode, builder):
        self.builders[mode] = builder

    def Build(self, target_name):
        logging.info("Building %s", target_name)
        target = self.targets_state.targets[target_name]
        definition =  target.GetModuleDefinition()
        builder = self.builders[definition.mode]

        logging.info("Picked %s for mode %s", builder, definition.mode)
        
        context = BuildingContext(self.targets_state.targets,
                self.build_results, definition.mode)
        
        for start_handler in self.build_start_handlers:
            start_handler(target_name)
        result = builder.Build(context, target_name)
        for finish_handler in self.build_finish_handlers:
            finish_handler(target_name, result)

        logging.info("Result for %s: %s", target_name, result)
        self.build_results[target_name] = result
        logging.info("All results: %s", self.build_results)
    
    def GetBuildResult(self, target_name):
        return self.build_results[target_name]

class TargetsState(object):
    def __init__(self):
        self.targets = {}

class BuildTracker(object):
    def __init__(self, graph, targets_state, builder, compilation_database,
            threading_manager):
        self.targets_state = targets_state
        self.threading_manager = threading_manager
        self.modified = set()
        self.graph = graph
        self.builder = builder
        self.compilation_database = compilation_database

    def GetBuildResult(self, target_name):
        return self.builder.GetBuildResult(target_name)

    def AddTarget(self, target):
        self.targets_state.targets[target.GetName()] = target
        self.modified.add(target.GetName())
    
    def RemoveTarget(self, target_name):
        del self.targets_state.targets[target_name]
        if target_name in self.modified:
            self.modified.remove(target_name)

    def ReloadTarget(self, target):
        self.targets_state.targets[target.GetName()] = target
        self.modified.add(target.GetName())

    def ResetTarget(self, target_name):
        self.modified.add(target_name)
       
    def GetTarget(self, target_name):
        return self.targets_state.targets[target_name]

    def Build(self):
        logging.info("Must build %s", sorted(self.modified))
        while self.modified:
            logging.info("Modified %s", self.modified)
            ready_to_build = set()
            for target_name in self.modified:
                dependencies = self.graph.GetDependencies(target_name)
                logging.info("Deps of %s are %s", target_name, dependencies)
                if not self.modified.intersection(dependencies):
                    ready_to_build.add(target_name)
            if ready_to_build:
                logging.info("Building wave %s", sorted(ready_to_build))
                executor = self.threading_manager.GetThreadPool("wave")
                completion_futures = []
                for ready_to_build_target_name in ready_to_build:
                    result = executor.submit(
                            lambda: self.builder.Build(ready_to_build_target_name))
                    completion_futures.append(result)
                for completion_future in completion_futures:
                    completion_future.result()

                self.modified = self.modified - ready_to_build
            else:
                if self.modified:
                    logging.warning("Some targets cannot be built %s",
                            sorted(self.modified))
                break
        self.modified = set()
        self.compilation_database.Write()
