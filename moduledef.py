import common

import logging
import os

class ModuleDefinition(object):
    def __init__(self):
        self.deps = []
        self.cflags = []
        self.lflags = []
        self.pkg_config = []
        self.env = {
            "deps": self.deps,
            "pkg_config": self.pkg_config,
            "cflags": self.cflags,
            "lflags": self.lflags,
            "mode": "c++"
        }
    
    def PostProcess(self):
        if "/" not in self.env["mode"]:
            self.env["mode"] = self.env["mode"] + "/default"
        del self.env["__builtins__"]

    def GetEnv(self):
        return self.env

class Evaluator(object):
    
    def GetModuleDefinitionForPath(self, path):
        return os.path.join(path, common.CONF_NAME)

    def RefreshModuleDefinition(self, target):
        if not target.Exists():
            raise common.Error("%s does not exist" % target)
        logging.info("Reading module definitions for %s", target)

        current_module_def_dir = target.GetRootDir()
        module_definition_paths = []
        
        for dir_in_path in [""]+target.GetName().split("/"):
            current_module_def_dir = os.path.join(current_module_def_dir, dir_in_path)
            module_definition_paths.append(
                    self.GetModuleDefinitionForPath(current_module_def_dir))
            
        module_definition = ModuleDefinition()
        for module_definition_path in module_definition_paths:
            if os.path.exists(module_definition_path):
                logging.info("Reading %s...", module_definition_path)
                with open(module_definition_path, "r") as f:
                    exec(f.read(), module_definition.GetEnv()) 
            else:
                logging.debug("No module definition at %s found.",
                        module_definition_path)
        module_definition.PostProcess()
        target.SetModuleDefinition(module_definition)
    

