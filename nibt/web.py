import pkg_resources

import logging

import asyncio
from aiohttp import web
import os.path
import mimetypes
import threading

class WebUIServer(object):
    
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.app = web.Application()
        self.app.router.add_route("GET", "/ws", self.WebSocket)
        self.app.router.add_route("GET", r"/{path:.*}", self.ServeResources)
    
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

        ws = web.WebSocketResponse()
        ws.start(request)

        while True:
            try:
                data = yield from ws.receive_str()
                if data == 'close':
                    ws.close()
                else:
                    ws.send_str(data + '/answer')
            except web.WebSocketDisconnectedError as exc:
                print(exc.code, exc.message)
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
            return web.Response(
                body=data,
                headers={"Content-Type": mime_type[0]}
            )
        except FileNotFoundError as e:
            logging.error("Unable to serve file %s", path)
            return web.Response(status=404, body=("Not found: '%s'" % path).encode())
    
