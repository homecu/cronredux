"""
Handle task monitoring and scheduling.
"""

import asyncio
import datetime
import subprocess
import time
from concurrent import futures


class Task(object):
    """ Encapsulate a repeated task. """

    def __init__(self, crontab, cmd):
        self.crontab = crontab
        self.cmd = cmd
        self.last_eta = crontab.next()

    def __str__(self):
        return '<Task: %s>' % self.cmd

    def __call__(self):
        return subprocess.check_output(self.cmd, shell=True,
                                       universal_newlines=True,
                                       stderr=subprocess.STDOUT)


class Scheduler(object):
    """ Manage execution and scheduling of tasks. """

    def __init__(self, tasks, args, notifier, loop):
        self.tasks = tasks
        self.args = args
        self.notifier = notifier
        self.loop = loop
        self.active = dict((x, []) for x in tasks)
        workers = self.args.max_concurrency
        self.executor = futures.ThreadPoolExecutor(max_workers=workers)

    @asyncio.coroutine
    def run(self):
        """ Babysit the task submission process. """
        while True:
            for task in self.tasks:
                done = [x for x in self.active[task] if x.done()]
                for x in done:
                    try:
                        output = x.result()
                    except subprocess.CalledProcessError as e:
                        self.notifier.error('Task Error: `%s`\n```\n%s```'
                                            % (task, e.output))
                    else:
                        if self.args.notify_stdout:
                            self.notifier.info('Task Success: `%s`\n'
                                               '```\n%s```' % (task, output))
                    self.active[task].remove(x)
            for task in self.tasks:
                eta = task.crontab.next()
                # look for rollover as our exec trigger.
                if eta > task.last_eta:
                    if self.active[task] and not self.args.allow_overlap:
                        self.notifier.warning('Skipping `%s` because a '
                                              'previous task is still '
                                              'active.' % task)
                    else:
                        self.enqueue_task(task)
                task.last_eta = eta
            yield from asyncio.sleep(1)

    def enqueue_task(self, task):
        """ Submit a task to the executor (thread pool). """
        f = self.loop.run_in_executor(self.executor, self.run_task, task)
        self.active[task].append(f)
        return f

    def run_task(self, task):
        """ Run process from an Executor context. """
        if self.args.notify_exec:
            self.notifier.info('Starting: `%s`' % task)
            start = time.monotonic()
        try:
            return task()
        finally:
            if self.args.notify_exec:
                took = datetime.timedelta(seconds=time.monotonic() - start)
                self.notifier.info('Finished: `%s` in %s' % (task, took))
