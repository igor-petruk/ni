#!/usr/bin/python

# import collections
# import glob
# import hashlib
# import json
# import os
# import re
# import subprocess
# import sys
# import tempfile
# import functools
# import threading
# from time import sleep
# import random
#

import logging

import dbus.service
import dbus.mainloop.glib

from gi.repository import Gio, GObject

APP_NAME="nihd"

APP_SVC_NAME="com.nid.Builder"
APP_SVC_PATH="/com/nid/Builder"

class CommandError(dbus.DBusException):
    pass


class DBusInterface(dbus.service.Object):

    def __init__(self, manager, threading_manager):
        self.manager = manager
        self.threading_manager = threading_manager
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(APP_SVC_NAME, bus=self.bus)
        dbus.service.Object.__init__(self, bus_name, APP_SVC_PATH)

    def _GetPool(self):
        return self.threading_manager.GetThreadPool("dbus")

    def _Execute(self, fn, reply_handler, error_handler):
        def func_wrapper():
            try:
                return fn()
            except Exception as e:
                logging.exception("Dbus call failed")
                return CommandError(str(e))

        def done_callback(ft):
            if isinstance(ft.result(), CommandError):
                error_handler(ft.result())
            else:
                reply_handler(ft.result())

        future = self._GetPool().submit(func_wrapper)
        future.add_done_callback(done_callback)


    @dbus.service.method(dbus_interface=APP_SVC_NAME,
                         in_signature="s",
                         async_callbacks=("reply_handler", "error_handler"))
    def AddTarget(self, target_name, reply_handler, error_handler):
        def Body():
            self.manager.AddActiveTarget(str(target_name))
            return "ok"
        self._Execute(Body, reply_handler, error_handler)

    @dbus.service.method(dbus_interface=APP_SVC_NAME,
                         in_signature="s",
                         async_callbacks=("reply_handler", "error_handler"))
    def BuildTarget(self, target_name, reply_handler, error_handler):
        def Body():
            build_results = self.manager.BuildTarget(str(target_name))
            broken = []
            for build_result in build_results:
                if not build_result.ok():
                    broken.append(build_result)
            if not broken:
                return {
                    "status": "ok"
                }
            else:
                return {
                    "status": "failure",
                    "msg": "\n".join([b.GetErrorMessage() for b in broken])
                }
        self._Execute(Body, reply_handler, error_handler)
    
    @dbus.service.method(dbus_interface=APP_SVC_NAME,
                         in_signature="s",
                         async_callbacks=("reply_handler", "error_handler"))
    def RemoveTarget(self, target_name, reply_handler, error_handler):
        def Body():
            self.manager.RemoveActiveTarget(str(target_name))
            return "ok"
        self._Execute(Body, reply_handler, error_handler)
    


    def Run(self):
        GObject.MainLoop().run()



