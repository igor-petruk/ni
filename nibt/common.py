import os.path

import logging


class ExecutableBuildResult(object):
    def GetExecutablePath(self):
        raise NotImplemented()


class SuccessfulBuildResult(object):
    def ok(self):
        return True

class FailedBuildResult(object):
    def __init__(self, error_msg, causes=[]):
        self.msg = error_msg
        self.causes = causes
        logging.info("Failed %s %s", error_msg, causes)

    def ok(self):
        return False

    def GetErrorMessage(self, indent=""):
        if not self.causes:
            return indent+self.msg
        else:
            causes_msg = [i.GetErrorMessage().replace("\n","\n "+indent)
                    for i in self.causes]
            return "%s%s, because\n%s" % (indent, self.msg,
                                          "\n".join(causes_msg))
    
    def __str__(self):
        return "FailedBuildResult(%s)" % self.GetErrorMessage()

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
        return os.path.join(self.GetObjDir(), os.path.dirname(self.GetName()))
    
    def GetOutDir(self):
        return os.path.join(self.GetRootDir(), "out")
    
    def Exists(self):
        return os.path.exists(self.GetModuleDir())
