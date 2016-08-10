"""
Support for notifications.
"""

import requests
import shellish


class PrintNotifier(object):
    """ A basic interface for sending notifications to stdout. """

    def info(self, message):
        shellish.vtmlprint("<blue>INFO: %s</blue>" % message)

    def warning(self, message):
        shellish.vtmlprint("<yellow>WARN: %s</yellow>" % message)

    def error(self, message):
        shellish.vtmlprint("<red>ERROR: %s</red>" % message)


class SlackNotifier(object):
    """ Send messages to a slack webhook. """

    default_username = 'Cronredux'
    default_icon_emoji = ':calendar:'

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

    def post(self, data):
        payload = self.default_payload.copy()
        payload.update(data)
        return requests.post(self.webhook, json=payload)

    def log(self, level, color, message):
        self.post({
            "attachments": [{
                "pretext": level,
                "title": level,
                "text": message,
                "color": color,
                "mrkdwn_in": ["text"]
            }]
        })

    def info(self, message):
        return self.log('INFO', '#99cc33', message)

    def warning(self, message):
        return self.log('WARN', 'yellow', message)

    def error(self, message):
        return self.log('ERROR', '#ff0000', message)
