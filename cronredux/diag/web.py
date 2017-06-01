"""
Diagnostic web server endpoints.
"""

import aiohttp_jinja2
import asyncio
import jinja2
import os
import pendulum
import platform
import shellish
from aiohttp import web


class DiagService(object):
    """ Diagnostic Web Service. """

    platform_info = {
        "system": platform.system(),
        "platform": platform.platform(),
        "node": platform.node(),
        "dist": ' '.join(platform.dist()),
        "python": platform.python_version()
    }
    ui_dir = os.path.join(os.path.dirname(__file__), 'ui')

    def __init__(self, tasks, args, loop, sched=None, plain=False):
        self.tasks = tasks
        self.args = args
        self.loop = loop
        self.tpl_context = {
            "environ": os.environ,
            "args": args,
            "tasks": tasks,
            "tasks_by_id": dict((x.ident, x) for x in tasks),
            "task_execs": lambda: dict(((x.task.ident, x.ident), x)
                                       for x in sched.history),
            "platform": self.platform_info,
            "ui_dir": self.ui_dir,
            "started": pendulum.now(),
            "pendulum": pendulum,
            "sched": sched
        }
        self.plain_output = plain

    @asyncio.coroutine
    def start(self):
        self.app = web.Application(loop=self.loop)
        tpl_loader = jinja2.FileSystemLoader(self.ui_dir)
        env = aiohttp_jinja2.setup(self.app, loader=tpl_loader)
        env.globals.update({
            "sorted": sorted
        })
        self.app.router.add_route('GET', '/', self.index_redir)
        self.app.router.add_route('GET', '/health', self.health)
        self.app.router.add_route('GET', '/ui/{path}', self.tpl_handler)
        self.app.router.add_static('/ui/static',
                                   os.path.join(self.ui_dir, 'static'))
        self.handler = self.app.make_handler()
        listen = self.args.diag_addr, self.args.diag_port
        self.server = yield from self.loop.create_server(self.handler, *listen)
        shellish.vtmlprint('<b>Running diag web server</b>: '
                           '<blue><u>http://%s:%s</u></blue>' % listen,
                           plain=self.plain_output)

    @asyncio.coroutine
    def index_redir(self, request):
        return web.HTTPFound('/ui/index.html')

    @asyncio.coroutine
    def health(self, request):
        return web.json_response({
            "platform_info": self.platform_info,
            "tasks": [x.cmd for x in self.tasks],
        })

    @asyncio.coroutine
    def tpl_handler(self, request):
        path = request.match_info['path']
        context = self.tpl_context.copy()
        context['request'] = request
        return aiohttp_jinja2.render_template(path, request, context)

    @asyncio.coroutine
    def cleanup(self):
        self.server.close()
        yield from self.server.wait_closed()
        yield from self.app.shutdown()
        yield from self.handler.finish_connections(1)
        yield from self.app.cleanup()
