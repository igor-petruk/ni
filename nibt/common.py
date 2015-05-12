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
    def __init__(self, name):
        logging.info("Created Target object %s", name)
        self._name = name
        self._module_definition = None

    def SetModuleDefinition(self, module_definition):
        logging.info("Setting moduledef or target %s: %s", self._name, module_definition)
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

