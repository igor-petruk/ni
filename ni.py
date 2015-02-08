#!/usr/bin/python

import dbus
import sys

bus = dbus.SessionBus()
proxy = bus.get_object(
    'com.nid.Builder',
    '/com/nid/Builder')

result = proxy.BuildTarget(sys.argv[1])
if result["status"] == "ok":
    sys.exit(0)
else:
    print(str(result["msg"]))
    sys.exit(1)
