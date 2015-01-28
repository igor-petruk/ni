import common

import logging
import os

class Config(object):
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
    
    def GetConfForPath(self, path):
        return os.path.join(path, common.CONF_NAME)

    def RefreshConfig(self, target):
        if not target.Exists():
            raise common.Error("%s does not exist" % target)
        logging.info("Reading configs for %s", target)

        current_config_dir = target.GetRootDir()
        config_files = []
        
        for dir_in_path in [""]+target.GetName().split("/"):
            current_config_dir = os.path.join(current_config_dir, dir_in_path)
            config_files.append(self.GetConfForPath(current_config_dir))
            
        config = Config()
        for config_file in config_files:
            if os.path.exists(config_file):
                logging.info("Reading %s...", config_file)
                with open(config_file, "r") as f:
                    exec(f.read(), config.GetEnv()) 
            else:
                logging.debug("No config at %s found.", config_file)
        config.PostProcess()
        target.SetConfig(config)
    

