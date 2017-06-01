"""
Support for notifications.
"""

import aiohttp
import asyncio
import json
import shellish
import time
import cronredux


class PrintNotifier(object):
    """ A basic interface for sending notifications to stdout. """

    @asyncio.coroutine
    def setup(self, loop):
        pass

    @asyncio.coroutine
    def info(self, title, message='', raw='', footer=None):
        shellish.vtmlprint("<b><blue>INFO: %s</blue></b>" % title,
                           plain=cronredux.PLAIN_OUTPUT)
        if message or raw:
            for line in (message + raw).splitlines():
                shellish.vtmlprint("    <blue>%s</blue>" % line,
                                   plain=cronredux.PLAIN_OUTPUT)
        if footer:
            shellish.vtmlprint("    <dim>%s</dim>" % footer,
                               plain=cronredux.PLAIN_OUTPUT)

    @asyncio.coroutine
    def warning(self, title, message='', raw='', footer=None):
        shellish.vtmlprint("<b>WARN: %s</b>" % title,
                           plain=cronredux.PLAIN_OUTPUT)
        if message or raw:
            for line in (message + raw).splitlines():
                shellish.vtmlprint("    %s" % line,
                                   plain=cronredux.PLAIN_OUTPUT)
        if footer:
            shellish.vtmlprint("<dim>%s</dim>" % footer,
                               plain=cronredux.PLAIN_OUTPUT)

    @asyncio.coroutine
    def error(self, title, message='', raw='', footer=None):
        shellish.vtmlprint("<b><red>ERROR: %s</red></b>" % title,
                           plain=cronredux.PLAIN_OUTPUT)
        if message or raw:
            for line in (message + raw).splitlines():
                shellish.vtmlprint("    <red>%s</red>" % line,
                                   plain=cronredux.PLAIN_OUTPUT)
        if footer:
            shellish.vtmlprint("    <dim>%s</dim>" % footer,
                               plain=cronredux.PLAIN_OUTPUT)


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
                                           'Retry in %f seconds.</red>' % retry,
                                           plain=cronredux.PLAIN_OUTPUT)
                        yield from asyncio.sleep(retry)
                        continue
                    else:
                        shellish.vtmlprint('<b><red>Slack Post Failed:</red> '
                                           '(%d) - %s</b>' % (resp.status,
                                           content),
                                           plain=cronredux.PLAIN_OUTPUT)
                yield from resp.release()
                break

    @asyncio.coroutine
    def log(self, level, color, title, message=None, raw=None, footer=None):
        text = []
        if message:
            text.append(message)
        if raw:
            if len(raw) > self.max_raw_size:
                head = raw[:self.max_raw_size // 2]
                tail = raw[-self.max_raw_size // 2:]
                text.append('```%s```\n>..._contents clipped_...\n```%s```' % (
                            head, tail))
            else:
                text.append('```%s```' % raw)
        payload = {
            "color": color,
            "pretext": '*%s*' % title,
            "fallback": title,
            "ts": time.time(),
            "mrkdwn_in": ['text', 'pretext', 'footer']
        }
        if text:
            payload['text'] = '\n'.join(text)
        if footer:
            payload['footer'] = footer
        yield from self.post({"attachments": [payload]})

    @asyncio.coroutine
    def info(self, *args, **kwargs):
        yield from self.log('INFO', '#2200cc', *args, **kwargs)

    @asyncio.coroutine
    def warning(self, *args, **kwargs):
        yield from self.log('WARN', '#ffcc44', *args, **kwargs)

    @asyncio.coroutine
    def error(self, *args, **kwargs):
        yield from self.log('ERROR', '#cc4444', *args, **kwargs)
