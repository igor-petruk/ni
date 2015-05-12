from nibt import common

import copy
import logging
import os


class ModuleDefinitionFactory(object):
    
    def _BuildClassCopy(self):
        new_class = type(type(self).__name__, (type(self), ), {})
        for key, value in type(self).__dict__.items():
            if not key.startswith("__"):
                setattr(new_class, key, copy.deepcopy(value))
        return new_class

    def __init__(self):
        for key, value in type(self).__dict__.items():
            if not key.startswith("__"):
                setattr(self, key, copy.deepcopy(value))

    def __repr__(self):
        return "%s%s" % (type(self).__name__, self.__dict__,)


class CppLibrary(ModuleDefinitionFactory):
    mode = "c++/library"
    pkg_config = []
    cflags = []
    lflags = []
    deps = []
    sources = None


class CppBinary(ModuleDefinitionFactory):
    mode = "c++/binary"
    pkg_config = []
    lflags = []
    deps = []
    binary_name = None


class ModuleDefinitionAccumulator(object):
    def __repr__(self):
        return "ModuleDefinitionAccumulator%s" % (self.__dict__,)

class TargetsDefinitionAccumulator(object):
    def __init__(self, target_factories_list):
        self.targets_dict = {i.__name__ : i()._BuildClassCopy() for i in target_factories_list}
        for target_factory_name, factory in self.targets_dict.items():
            setattr(self, target_factory_name, factory)

    def __repr__(self):
        expanded_targets_dict = {k:dict({attr:value for attr,value in factory.__dict__.items() if not attr.startswith("_")}) for k, factory in self.targets_dict.items()}
        return "TargetsDefinitionAccumulator%s" % (dict(expanded_targets_dict),)

class ModuleEvaluationContext(object):
    def __init__(self, targets):
        self.module_definition_accumulator = ModuleDefinitionAccumulator()
        logging.info("Starting evaluation context with targets: %s", targets)
        self.env = {
            "modules": self.module_definition_accumulator,
            "targets": targets,
        }
    
    def PostProcess(self):
        b_key = "__builtins__"
        if b_key in self.env:
            del self.env[b_key]
        logging.info("Final module definition: %s", self.env["modules"])

    def GetEnv(self):
        return self.env


class DirectoryModulesConfiguration(object):
    def __init__(self, relative_dir, explicit_targets):
        self.explicit_targets = explicit_targets
        self.relative_dir = relative_dir

    def GetConfig(self, target_name):
        if not target_name.startswith(self.relative_dir):
            raise ValueError("DirectoryModulesConfiguration for '"+self.relative_dir+"' does not"
                    " contain configuration for '+"+target_name+"'")
        target_in_dir = target_name[len(self.relative_dir)+1:]
        logging.info("Querying %s for %s", self.explicit_targets, target_in_dir)
        return self.explicit_targets[target_in_dir]
    
    def __repr__(self):
        return "DirectoryModulesConfiguration(explicit=%s)" % (self.explicit_targets,)

class Evaluator(object):
    def __init__(self, target_factories, configuration):
        self._moddef_filename = configuration.Get(
                "general","module_definition_filename")
        self._root_dir = configuration.GetExpandedDir(
                "projects","root_dir")
        self._target_factories = target_factories
        
    def GetModuleDefinitionForPath(self, path):
        return os.path.join(path, self._moddef_filename)

    def LoadModuleDefinition(self, relative_target_dir):
        logging.info("Reading module definitions for configs in %s", relative_target_dir)

        current_module_def_dir = self._root_dir

        targets_definition_accumulator = TargetsDefinitionAccumulator(self._target_factories)

        module_evaluation_context = ModuleEvaluationContext(targets_definition_accumulator)
        relative_dir = ""
        found_targets = {}
        for dir_in_path in [""]+relative_target_dir.split("/"):
            relative_dir = os.path.join(relative_dir, dir_in_path)
            logging.info("Relative dir: '%s'", relative_dir)
            module_evaluation_context = ModuleEvaluationContext(targets_definition_accumulator)
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
            
            acc = module_evaluation_context.module_definition_accumulator
            discovered_modules = acc.__dict__
            
            logging.info("Discovered modules %s", discovered_modules)

            for local_target_name, module_definition in discovered_modules.items():
                found_targets[local_target_name] = module_definition
        
        dir_modules = DirectoryModulesConfiguration(
                relative_dir,
                found_targets)
        
        logging.info("Parsed following modules: %s", dir_modules)

        return dir_modules
    

