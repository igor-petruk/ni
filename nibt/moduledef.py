from nibt import common

import logging
import os

def _CopyListIfExists(source, destination, attr, default):
    new_val = default
    if source is not None:
        new_val = getattr(source, attr)[:]
    setattr(destination, attr, new_val)

def _CopyIfExists(source, destination, attr, default):
    new_val = default
    if source is not None:
        new_val = getattr(source, attr)
    setattr(destination, attr, new_val)

class ModuleDefinition(object):
    def __init__(self, previous=None):
        _CopyListIfExists(previous, self, "pkg_config", [])
        _CopyListIfExists(previous, self, "lflags", [])
        _CopyListIfExists(previous, self, "cflags", [])
        _CopyListIfExists(previous, self, "deps", [])
        _CopyIfExists(previous, self, "mode", "c++/default")
        _CopyIfExists(previous, self, "binary_name", None)

    def __repr__(self):
        return "ModuleDefinition%s" % (self.__dict__,)


class ModuleDefinitionAccumulator(object):
    def __init__(self, current_common):
        self._current_common = current_common
        self._modules_dict = {}
    
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError()
        logging.info("Getting attr %s", name)
        definition = ModuleDefinition(self._current_common)
        setattr(self, name, definition)
        self._modules_dict[name] = definition
        return definition

    def __repr__(self):
        return "ModuleDefinitionAccumulator%s" % (self._modules_dict,)


class ModuleEvaluationContext(object):
    def __init__(self, previous_common=None):
        self.deps = []
        self.cflags = []
        self.lflags = []
        self.pkg_config = []
        self.current_common = ModuleDefinition(previous_common)
        self.module_definition_accumulator = ModuleDefinitionAccumulator(self.current_common)
        self.env = {
            "common": self.current_common,
            "modules": self.module_definition_accumulator,
        }
    
    def PostProcess(self):
        del self.env["__builtins__"]
        logging.info("Final module definition: %s", self.env)

    def GetEnv(self):
        return self.env


class DirectoryModulesConfiguration(object):
    def __init__(self, relative_dir, common, explicit_targets):
        self.common = common
        self.explicit_targets = explicit_targets
        self.relative_dir = relative_dir

    def GetConfig(self, target_name):
        if not target_name.startswith(self.relative_dir):
            raise ValueError("DirectoryModulesConfiguration for '"+self.relative_dir+"' does not"
                    " contain configuration for '+"+target_name+"'")
        target_in_dir = target_name[len(self.relative_dir)+1:]
        logging.info("Querying %s for %s", self.explicit_targets, target_in_dir)
        return self.explicit_targets.get(target_in_dir, self.common) 
    
    def __repr__(self):
        return "DirectoryModulesConfiguration(explicit=%s, common=%s" % (self.explicit_targets, self.common)

class Evaluator(object):
    def __init__(self, configuration):
        self._moddef_filename = configuration.Get(
                "general","module_definition_filename")
        self._root_dir = configuration.GetExpandedDir(
                "projects","root_dir")
        
    def GetModuleDefinitionForPath(self, path):
        return os.path.join(path, self._moddef_filename)

    def LoadModuleDefinition(self, relative_target_dir):
        logging.info("Reading module definitions for configs in %s", relative_target_dir)

        current_module_def_dir = self._root_dir
        
        module_evaluation_context = ModuleEvaluationContext()
        relative_dir = ""
        found_targets = {}
        for dir_in_path in [""]+relative_target_dir.split("/"):
            relative_dir = os.path.join(relative_dir, dir_in_path)
            logging.info("Relative dir: '%s'", relative_dir)
            module_evaluation_context = ModuleEvaluationContext(module_evaluation_context.current_common)
            current_module_def_dir = os.path.join(current_module_def_dir, dir_in_path)
            module_definition_path = self.GetModuleDefinitionForPath(current_module_def_dir)
            if os.path.exists(module_definition_path):
                logging.info("Reading %s...", module_definition_path)
                with open(module_definition_path, "r") as f:
                    exec(f.read(), module_evaluation_context.GetEnv()) 
            else:
                logging.debug("No module definition at %s found.",
                        module_definition_path)
            module_evaluation_context.PostProcess()
            
            discovered_modules = module_evaluation_context.module_definition_accumulator._modules_dict
            
            for local_target_name, module_definition in discovered_modules.items():
                found_targets[local_target_name] = module_definition
        
        dir_modules = DirectoryModulesConfiguration(
                relative_dir,
                module_evaluation_context.current_common,
                found_targets)
        
        logging.info("Parsed following modules: %s", dir_modules)

        return dir_modules
    

