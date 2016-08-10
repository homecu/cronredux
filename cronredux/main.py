"""
A newage cron service.
"""

import crontab
import shellish
from . import cronparser, notification, scheduler


class CronReduxCommand(shellish.Command):
    """ Cronredux.

    A reimagined cron executor. """

    name = "cronredux"
    min_resolution = 60

    def setup_args(self, parser):
        self.add_file_argument('crontab', help='Crontab file to read.')
        self.add_argument('--verbose', action='store_true')
        self.add_argument('--slack-webhook', help='WebHook URL for slack '
                          'notifications.')
        self.add_argument('--slack-channel', help='Override the default '
                          'slack channel.')
        self.add_argument('--slack-username', help='Override the default '
                          'slack username.')
        self.add_argument('--slack-icon-emoji', help='Override the default '
                          'slack icon emoji.')
        self.add_argument('--notify-stdout', action='store_true',
                          help='Enable notifications for stdout of each task '
                          'execution.')
        self.add_argument('--notify-exec', action='store_true',
                          help='Enable notifications for each task execution.')
        self.add_argument('--slow-exec-warning', default=60, help='Time in '
                          'seconds before a warning is generated about slow '
                          'task execution.')
        self.add_argument('--backlog-warning', default=60, help='Time in '
                          'seconds before a warning is generated about a '
                          'delayed task execution due to a backlog.')
        self.add_argument('--max-concurrency', default=10, help='Max tasks '
                          'that will be allowed to run concurrently.')
        self.add_argument('--allow-overlap', action='store_true')

    def run(self, args):
        self.args = args
        tasks = []
        with args.crontab() as f:
            for spec, command in cronparser.parsef(f):
                if args.verbose:
                    shellish.vtmlprint("<b>Processing:</b> <blue>%s</blue> %s"
                                       % (spec, command))
                tasks.append(scheduler.Task(crontab.CronTab(spec), command))
        if args.slack_webhook:
            n = notification.SlackNotifier(args.slack_webhook,
                                           channel=args.slack_channel,
                                           username=args.slack_username,
                                           icon_emoji=args.slack_icon_emoji)
        else:
            n = notification.PrintNotifier()
        sched = scheduler.Scheduler(tasks, args, n)
        sched.run_forever()


def main():
    CronReduxCommand()()
