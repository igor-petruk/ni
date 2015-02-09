#!/usr/bin/python

import dbus
import sys
import logging
import os

LOGGING_FORMAT = "[%(filename)s:%(lineno)s] %(message)s"
logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)

bus = dbus.SessionBus()
proxy = bus.get_object(
    'com.nid.Builder',
    '/com/nid/Builder')

def ReportIfError(result):
    if result["status"] != "ok":
        print(str(result["msg"]))
        sys.exit(1)
    else:
        return result

def HandleBuild(argv):
    ReportIfError(proxy.BuildTarget(argv[0]))

def HandleRun(argv):
    result = ReportIfError(proxy.BuildTarget(argv[0]))
    executables = [str(e) for e in result["executables"]]
    if len(executables) == 0:
        print("No executable is produced by target")
        sys.exit(1)
    elif len(executables) > 1:
        print("Multiple executables, selection not implemented: %s" % executables)
        sys.exit(1)
    else:
        executable = executables[0]
        os.execv(executable, argv)

def HandleAdd(argv):
    ReportIfError(proxy.AddTarget(argv[0]))

def HandleRemove(argv):
    ReportIfError(proxy.RemoveTarget(argv[0]))

def HandleComplete(argv):
    result = ReportIfError(proxy.Complete(argv[1]))
    for completion in result["completions"]:
        print(str(completion))

commands = {
    "run": HandleRun,
    "build": HandleBuild,
    "add": HandleAdd,
    "remove": HandleRemove,
    "complete": HandleComplete,
}

command = sys.argv[1]
argv = sys.argv[2:]

if command in commands:
    commands[command](argv)
    sys.exit(0)
else:
    print("Not supported command '%s'. Supported are %s" % (
        command, sorted(commands.keys())))
    sys.exit(1)
    
