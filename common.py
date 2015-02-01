import os.path

import logging

class Error(Exception):
    pass

class Target(object):
    def __init__(self, root_dir, name):
        self._name = name
        self._root = root_dir
        self._module_definition = None

    def SetModuleDefinition(self, module_definition):
        self._module_definition = module_definition
    
    def GetModuleDefinition(self):
        return self._module_definition

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
