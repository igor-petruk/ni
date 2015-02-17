import pkg_resources

import logging

import aiohttp
import asyncio
from aiohttp import web
import os.path
import mimetypes
import threading

import json

class WebSocketStateEmitter(object):
    def __init__(self, stream_id):
        self.stream_id = stream_id
        self.websockets = set()
        self.websockets_lock = threading.RLock()

    def RegisterWebSocket(self, ws):
        with self.websockets_lock:
            self.websockets.add(ws)
            msg = {
                "sid": self.stream_id,
                "type": "init",
                "data": self.GetInitialStateDict()
            }
            msg_str = json.dumps(msg)
            ws.send_str(msg_str)

    def UnregisterWebSocket(self, ws):
        with self.websockets_lock:
            self.websockets.remove(ws)
    
    def EmitEvent(self, event):
        msg = {
            "sid": self.stream_id,
            "type": "event",
            "data": event
        }
        msg_str = json.dumps(msg) 
        with self.websockets_lock:
            for ws in self.websockets:
                ws.send_str(msg_str)

    def GetInitialStateDict(self):
        return {}

class TrackedTargetsStateEmitter(WebSocketStateEmitter):
    def __init__(self, graph):
        WebSocketStateEmitter.__init__(self, "tracked_targets")
        self.graph = graph
        self.graph.AddTrackedHandler(self.OnTargetAdded)
        self.graph.AddUntrackedHandler(self.OnTargetRemoved)
        self.graph.AddRefreshingHandler(self.OnTargetRefreshed)

    def GetInitialStateDict(self):
        state = {}
        for target, deps in self.graph.GetAllDependencies().items():
            state[target] = sorted(deps)
        return state
    
    def OnTargetAdded(self, target_name):
        self.EmitEvent({
            "action": "added",
            "target_name": target_name,
            "deps": sorted(self.graph.GetDependencies(target_name))
        })

    def OnTargetRemoved(self, target_name):
        self.EmitEvent({
            "action": "removed",
            "target_name": target_name,
        })

    def OnTargetRefreshed(self, target_name):
        self.EmitEvent({
            "action": "refreshed",
            "target_name": target_name,
            "deps": sorted(self.graph.GetDependencies(target_name))
        })

class BuildProcessStateEmitter(WebSocketStateEmitter):
    def __init__(self, builder):
        WebSocketStateEmitter.__init__(self, "build")
        self.builder = builder
        self.builder.AddBuildStartHandler(self.OnBuildStarted)
        self.builder.AddBuildFinishHandler(self.OnBuildFinished)

    def OnBuildStarted(self, target_name):
        self.EmitEvent({
            "action": "started",
            "target_name": target_name
        })

    def OnBuildFinished(self, target_name, result):
        msg = {
            "action": "finished",
            "target_name": target_name
        }
        assert len(result)==1
        if result[0].ok():
            msg["result"]="ok"
        else:
            msg["result"]="failed"
            msg["error"]=result[0].GetErrorMessage()
        self.EmitEvent(msg)

class WebUIServer(object):
    
    def __init__(self, emitters):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.app = web.Application()
        self.app.router.add_route("GET", "/ws", self.WebSocket)
        self.app.router.add_route("GET", r"/{path:.*}", self.ServeResources)
        self.websockets = set()
        self.emitters = emitters

    def Run(self):
        host = "127.0.0.1"
        port = 8787
        logging.info("Running WebUI at http://%s:%s/", host, port)
        f = self.loop.create_server(self.app.make_handler(), '0.0.0.0', port)
        srv = self.loop.run_until_complete(f)
        logging.info("Serving on %s", srv.sockets[0].getsockname())
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            logging.info("Interrupted web serving thread...")
            pass
    def Start(self):
        thread = threading.Thread(target=self.Run, daemon=True)
        thread.start()
 
    @asyncio.coroutine
    def WebSocket(self, request):
        peername = request.transport.get_extra_info('peername') 
        ws = web.WebSocketResponse()
        logging.info("WebSocket client connected: %s", peername)
        ws.start(request)
        
        for emitter in self.emitters:
            emitter.RegisterWebSocket(ws)

        while True:
            try:
                data = yield from ws.receive_str()
                if data == 'close':
                    ws.close()
            except aiohttp.errors.WSClientDisconnectedError as exc:
                logging.info("WebSocket client disconnected: %s", peername)
                for emitter in self.emitters:
                    emitter.UnregisterWebSocket(ws)
                return ws

    @asyncio.coroutine
    def ServeResources(self, request):
        path = request.match_info["path"]
        if not path:
            path = 'index.html'
        mime_type = mimetypes.guess_type(path)
        logging.info("Serving %s, type: %s", path, mime_type)
        try:
            data = pkg_resources.resource_string(__name__, os.path.join("data", path))
            headers = {}
            if mime_type[0]:
                headers["Content-Type"] = mime_type[0]
            return web.Response(
                body=data,
                headers=headers
            )
        except FileNotFoundError as e:
            logging.error("Unable to serve file %s", path)
            return web.Response(status=404, body=("Not found: '%s'" % path).encode())
    
