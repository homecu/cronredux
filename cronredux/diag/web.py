"""
Diagnostic web server endpoints.
"""

import asyncio
import os
import platform
from aiohttp import web


class DiagService(object):
    """ Diagnostic Web Service. """

    platform_info = {
        "system": platform.system(),
        "node": platform.node(),
        "dist": ' '.join(platform.dist()),
        "python": platform.python_version()
    }

    def __init__(self, tasks, args, loop):
        self.tasks = tasks
        self.args = args
        self.loop = loop

    @asyncio.coroutine
    def start(self):
        self.app = web.Application(loop=self.loop)
        self.app.router.add_route('GET', '/', self.index_redir)
        self.app.router.add_route('GET', '/health', self.health)
        self.app.router.add_static('/ui', os.path.dirname(__file__) + '/ui')
        self.handler = self.app.make_handler()
        self.server = yield from self.loop.create_server(self.handler,
                                                         self.args.diag_addr,
                                                         self.args.diag_port)

    @asyncio.coroutine
    def index_redir(self, request):
        return web.HTTPFound('/ui/index.html')

    @asyncio.coroutine
    def health(self, request):
        return web.json_response({
            "run_args": vars(self.args),
            "platform_info": self.platform_info,
            "tasks": self.tasks,
        })

    @asyncio.coroutine
    def cleanup(self):
        self.server.close()
        yield from self.server.wait_closed()
        yield from self.app.shutdown()
        yield from self.handler.finish_connections(1)
        yield from self.app.cleanup()
