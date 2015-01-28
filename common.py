import os.path

import logging

logging.basicConfig(level=logging.INFO) 

CONF_NAME="ni.py"
ROOT_ENV_VAR="NIH_PROJECT_ROOT"

class Error(Exception):
    pass

def GetRootFromEnv():
    return os.path.expanduser(os.environ[ROOT_ENV_VAR])

class Target(object):
    def __init__(self, name):
        project, module = name.split("/")
        self._project = project
        self._module = module
        self._root = GetRootFromEnv()
        self._config = None

    def SetConfig(self, config):
        self._config = config
    
    def GetConfig(self):
        return self._config

    def GetName(self):
        return "%s/%s" % (self._project, self._module)
    
    def __repr__(self):
        return "Target('%s')" % self.GetName()
    
    def __hash__(self):
        return hash(self.GetName())

    def __eq__(self, other):
        return self.GetName() == other.GetName()

    def GetProject(self):
        return self._project

    def GetModule(self):
        return self._module

    def GetRootDir(self):
        return self._root

    def GetRootConf(self):
        return os.path.join(self.GetRootDir(), CONF_NAME)

    def GetProjectDir(self):
        return os.path.join(self.GetRootDir(), self.GetProject())

    def GetProjectConf(self):
        return os.path.join(self.GetProjectDir(), CONF_NAME)

    def GetModuleDir(self):
        return os.path.join(self.GetProjectDir(), self.GetModule())

    def GetObjDir(self):
        return os.path.join(self.GetRootDir(), "obj")
    
    def GetTargetObjDir(self):
        return os.path.join(self.GetObjDir(), self.GetName())
    
    def GetOutDir(self):
        return os.path.join(self.GetRootDir(), "out")
    
    def GetProjectOutDir(self):
        return os.path.join(self.GetOutDir(), self.GetProject())

    def GetModuleConf(self):
        return os.path.join(self.GetModuleDir(), CONF_NAME)
   
    def Exists(self):
        return os.path.exists(self.GetModuleDir())
