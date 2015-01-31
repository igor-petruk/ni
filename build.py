import common
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
    def __init__(self, targets_state, compilation_database):
        self.targets_state = targets_state
        self.build_results = {}
        self.root = common.GetRootFromEnv()
        self.builders = {}
        self.compilation_database = compilation_database

    def RegisterBuilder(self, mode, builder):
        self.builders[mode] = builder

    def Build(self, target_name):
        logging.info("Building %s", target_name)
        target = self.targets_state.targets[target_name]
        env =  target.GetConfig().GetEnv()
        builder = self.builders[env["mode"]]

        logging.info("Picked %s for mode %s", builder, env["mode"])
        
        context = BuildingContext(self.targets_state.targets,
                self.build_results, env["mode"])

        result = builder.Build(context, target_name)
        logging.info("Result for %s: %s", target_name, result)
        self.build_results[target_name] = result
        self.compilation_database.Write()

class TargetsState(object):
    def __init__(self):
        self.targets = {}

class BuildTracker(object):
    def __init__(self, graph, targets_state, builder):
        self.targets_state = targets_state
        self.modified = set()
        self.graph = graph
        self.builder = builder

    def AddTarget(self, target):
        self.targets_state.targets[target.GetName()] = target
        self.modified.add(target.GetName())
    
    def RemoveTarget(self, target_name):
        del self.targets_state.targets[target_name]
        if target_name in self.modified:
            self.modified.remove(target_name)

    def ReloadTarget(self, target):
        self.target_state.targets[target.GetName()] = target
        self.modified.add(target.GetName())

    def ResetTarget(self, target_name):
        self.modified.add(target_name)
       
    def GetTarget(self, target_name):
        return self.targets_state.targets[target_name]

    def Build(self):
        logging.info("Must build %s", sorted(self.modified))
        while self.modified:
            ready_to_build = set()
            for target_name in self.modified:
                dependencies = self.graph.GetDependencies(target_name)
                if not self.modified.intersection(ready_to_build):
                    ready_to_build.add(target_name)
            if ready_to_build:
                logging.info("Building wave %s", sorted(ready_to_build))
                for ready_to_build_target_name in ready_to_build:
                    self.builder.Build(ready_to_build_target_name)
                self.modified = self.modified - ready_to_build
            else:
                if self.modified:
                    logging.warning("Some targets cannot be built %s",
                            sorted(self.modified))
                break
        self.modified = set()
