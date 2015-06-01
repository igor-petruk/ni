#!/usr/bin/python

import logging

import dbus
import dbus.service
import dbus.mainloop.glib
import glob
import os

from gi.repository import Gio, GObject

from nibt import common

APP_NAME="nihd"

APP_SVC_NAME="com.nid.Builder"
APP_SVC_PATH="/com/nid/Builder"

class CommandError(dbus.DBusException):
    pass

OK = {
    "status": "ok"
}

class DBusInterface(dbus.service.Object):

    def __init__(
            self, configuration, manager, threading_manager, watch_index,
            builder):
        self._root = configuration.GetExpandedDir("projects", "root_dir")
        self.manager = manager
        self.builder = builder
        self.watch_index = watch_index
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
            return OK
        self._Execute(Body, reply_handler, error_handler)
    
    
    @dbus.service.method(dbus_interface=APP_SVC_NAME,
                         in_signature="s",
                         out_signature="as")
    def GetCompilationFlags(self, file_name):
        root_prefix_len = len(self._root)
        rel_path = file_name[root_prefix_len+1:]
        targets = self.watch_index.GetMatchingTargets(rel_path)
        if not targets:
            logging.info("No compilations flags for '%s'" % rel_path)
            return []
        else:
            key = list(targets.keys())[0]
            if len(targets)>1:
                logging.warning(
                    "File '%s' is watched by multiple targets: "
                    "%s. Returing compilation flags for '%s'",
                    rel_path, targets, key)
            flags = self.builder.GetCompilationFlags(key)
            logging.info("Flags for '%s': %s", rel_path, flags)
            return flags

    @dbus.service.method(dbus_interface=APP_SVC_NAME,
                         in_signature="s",
                         async_callbacks=("reply_handler", "error_handler"))
    def BuildTarget(self, target_name, reply_handler, error_handler):
        def Body():
            build_results = self.manager.BuildTarget(str(target_name))
            broken = []
            executables = dbus.Array(signature="s")
            for build_result in build_results:
                if not build_result.ok():
                    broken.append(build_result)
                elif isinstance(build_result, common.ExecutableBuildResult):
                    executables.append(dbus.String(build_result.GetExecutablePath()))
            if not broken:
                return dbus.Dictionary({
                    "status": "ok",
                    "executables": executables,
                }, signature="sv")
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
            return OK
        self._Execute(Body, reply_handler, error_handler)
    
    @dbus.service.method(dbus_interface=APP_SVC_NAME,
                         in_signature="s",
                         async_callbacks=("reply_handler", "error_handler"))
    def Complete(self, prefix, reply_handler, error_handler):
        def Body():
            result = dbus.Array(signature="s")
            
            def Walk(relative):
                full = os.path.join(self._root, relative)
                logging.info("Walking '%s'", full)
                result.append(relative)
                for _, dirs, _ in os.walk(full):
                    for dir_name in dirs:
                        Walk(os.path.join(relative, dir_name))

            glob_expr = os.path.join(self._root, prefix)+"*"
            logging.info("Completing for glob prefix '%s'", glob_expr)
            for full_filename in glob.glob(glob_expr):
                if not os.path.isdir(full_filename):
                    continue
                relative = full_filename[(len(self._root)+1):]
                first_path = relative.split("/")
                if first_path[0] in set(["out","obj"]):
                    continue
                Walk(relative)

            return dbus.Dictionary({
                "status": "ok",
                "completions": result,
            }, signature="sv")
        self._Execute(Body, reply_handler, error_handler)

    def Run(self):
        logging.info("Running DBus service...")
        main_loop = GObject.MainLoop()
        first = True
        while first or main_loop.is_running():
            first = False
            try:    
                main_loop.run()
            except KeyboardInterrupt:
                main_loop.quit()


