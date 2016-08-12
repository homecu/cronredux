"""
Support for notifications.
"""

import aiohttp
import asyncio
import json
import shellish
import time


class PrintNotifier(object):
    """ A basic interface for sending notifications to stdout. """

    @asyncio.coroutine
    def setup(self, loop):
        pass

    def info(self, title, message='', raw='', footer=None):
        shellish.vtmlprint("<b><blue>INFO: %s</blue></b>" % title)
        if message or raw:
            for line in (message + raw).splitlines():
                shellish.vtmlprint("    <blue>%s</blue>" % line)
        if footer:
            shellish.vtmlprint("    <dim>%s</dim>" % footer)

    def warning(self, title, message='', raw='', footer=None):
        shellish.vtmlprint("<b><yellow>WARN: %s</yellow></b>" % title)
        if message or raw:
            for line in (message + raw).splitlines():
                shellish.vtmlprint("    <yellow>%s</yellow>" % line)
        if footer:
            shellish.vtmlprint("<dim>%s</dim>" % footer)

    def error(self, title, message='', raw='', footer=None):
        shellish.vtmlprint("<b><red>ERROR: %s</red></b>" % title)
        if message or raw:
            for line in (message + raw).splitlines():
                shellish.vtmlprint("    <red>%s</red>" % line)
        if footer:
            shellish.vtmlprint("    <dim>%s</dim>" % footer)


class SlackNotifier(object):
    """ Send messages to a slack webhook. """

    default_username = 'Cronredux'
    default_icon_emoji = ':calendar:'
    max_raw_size = 700

    def __init__(self, webhook_url, channel=None, username=None,
                 icon_emoji=None):
        self.webhook = webhook_url
        self.default_payload = p = {}
        if channel is not None:
            p['channel'] = channel
        p['username'] = username if username is not None else \
                        self.default_username
        p['icon_emoji'] = icon_emoji if icon_emoji is not None else \
                        self.default_icon_emoji

    @asyncio.coroutine
    def setup(self, loop):
        self.loop = loop
        headers = {'content-type': 'application/json'}
        self.session = aiohttp.ClientSession(loop=loop, headers=headers)
        self.lock = asyncio.Lock()

    @asyncio.coroutine
    def post(self, data):
        payload = self.default_payload.copy()
        payload.update(data)
        with (yield from self.lock):
            while True:
                resp = yield from self.session.post(self.webhook,
                                                    data=json.dumps(payload))
                if resp.status != 200:
                    content = yield from resp.json()
                    if resp.status == 429:  # rate limited
                        retry = content['retry_after']
                        shellish.vtmlprint('<red>Slack Rate Limit Reached: '
                                           'Retry in %f seconds.</red>' %
                                           retry)
                        yield from asyncio.sleep(retry)
                        continue
                    else:
                        shellish.vtmlprint('<b><red>Slack Post Failed:</red> '
                                           '(%d) - %s</b>' % (resp.status,
                                           content))
                yield from resp.release()
                break

    @asyncio.coroutine
    def log(self, level, color, title, message=None, raw=None, footer=None):
        if raw and len(raw) > self.max_raw_size:
            head = raw[:self.max_raw_size // 2]
            tail = raw[-self.max_raw_size // 2:]
            raw = '```%s```\n>..._contents clipped_...\n```%s```' % (head, tail)
        payload = {
            "color": color,
            "pretext": '*%s*' % title,
            "fallback": title,
            "ts": time.time(),
            "mrkdwn_in": ['text', 'pretext', 'footer']
        }
        text = []
        if message:
            text.append(message)
        if raw:
            text.append(raw)
        if text:
            payload['text'] = '\n'.join(text)
        if footer:
            payload['footer'] = footer
        yield from self.post({"attachments": [payload]})

    def info(self, *args, **kwargs):
        self.loop.create_task(self.log('INFO', '#2200cc', *args, **kwargs))

    def warning(self, *args, **kwargs):
        self.loop.create_task(self.log('WARN', '#ffcc44', *args, **kwargs))

    def error(self, *args, **kwargs):
        self.loop.create_task(self.log('ERROR', '#cc4444', *args, **kwargs))
