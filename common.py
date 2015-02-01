import os.path

import logging

CONF_NAME="ni.py"
ROOT_ENV_VAR="NIH_PROJECT_ROOT"

class Error(Exception):
    pass

def GetRootFromEnv():
    return os.path.expanduser(os.environ[ROOT_ENV_VAR])

class Target(object):
    def __init__(self, name):
        self._name = name
        self._root = GetRootFromEnv()
        self._config = None

    def SetConfig(self, config):
        self._config = config
    
    def GetConfig(self):
        return self._config

    def GetName(self):
        return self._name
    
    def __repr__(self):
        return "Target('%s')" % self.GetName()
    
    def __hash__(self):
        return hash(self.GetName())

    def __eq__(self, other):
        return self.GetName() == other.GetName()

    def GetRootDir(self):
        return self._root

    def GetModuleDir(self):
        return os.path.join(self.GetRootDir(), self.GetName())

    def GetObjDir(self):
        return os.path.join(self.GetRootDir(), "obj")
    
    def GetTargetObjDir(self):
        return os.path.join(self.GetObjDir(), self.GetName())
    
    def GetOutDir(self):
        return os.path.join(self.GetRootDir(), "out")
    
    def Exists(self):
        return os.path.exists(self.GetModuleDir())
