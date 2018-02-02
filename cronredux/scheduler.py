"""
Handle task monitoring and scheduling.
"""

import asyncio
import collections
import functools
import itertools
import pendulum
import shellish
import subprocess
import textwrap
import traceback


class TaskExecContext(object):
    """ A data structure representing a task execution.  Status and info about
    an invocation is kept here and these instances are used to track activity.
    """

    def __init__(self, task, loop):
        self.started = None
        self.finished = None
        self.returncode = None
        self.output = ''
        self.state = 'init'
        self.ident = next(task.context_identer)
        self.task = task
        self.loop = loop

    def __str__(self):
        return '<TaskExecContext %d [%s]> for %s' % (self.ident, self.state,
                                                     self.task)

    def set_start(self):
        assert self.state == 'init'
        self.started = pendulum.now()
        self.state = 'start'

    def set_finish(self, returncode, output):
        assert self.state == 'start'
        self.finished = pendulum.now()
        self.state = 'finish'
        self.output = output
        self.returncode = returncode

    @property
    def elapsed(self):
        """ Increments for active tasks and when finished gives the total
        execution time. """
        if self.started is None:
            return pendulum.Interval()
        if self.finished is None:
            return pendulum.now() - self.started
        else:
            return self.finished - self.started

    def is_error(self):
        if self.state != 'finish':
            raise TypeError('Task is still running')
        return not not self.returncode

    def is_done(self):
        return self.state == 'finished'

    @asyncio.coroutine
    def run_task(self):
        self.set_start()
        process, output = yield from self.task(self.loop)
        self.set_finish(process.returncode, output.decode())


class Task(object):
    """ Encapsulate a repeated task. """

    identer = itertools.count()

    def __init__(self, crontab, cmd):
        self.ident = next(self.identer)
        self.context_identer = itertools.count()
        self.crontab = crontab
        self.cmd = cmd
        self.last_eta = crontab.next(default_utc=False)
        self.run_count = 0
        self.elapsed = pendulum.Interval()

    def __str__(self):
        dots = shellish.beststr("…", '...')
        cmd = textwrap.shorten(self.cmd, width=40, placeholder=dots)
        return '<Task %d: cmd="%s">' % (self.ident, cmd)

    def next_run(self):
        """ Estimated time of next run. """
        return pendulum.Interval(seconds=self.crontab.next(default_utc=False))

    @asyncio.coroutine
    def __call__(self, loop):
        start = pendulum.now()
        ps = yield from asyncio.create_subprocess_shell(
            self.cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            loop=loop)
        output = (yield from ps.communicate())[0]
        self.elapsed += pendulum.now() - start
        self.run_count += 1
        return ps, output

    def ready(self):
        """ Returns true when this task should be run.  If this function is not
        called as or more frequently than the cron period then it will skip or
        even never return true.  It is advised to call this at least double the
        minimum cron period of 1 minute, e.g. 30 seconds. """
        next_eta = self.crontab.next(default_utc=False)
        r = self.last_eta < next_eta  # rollover occurred == ready
        self.last_eta = next_eta
        return r


class Scheduler(object):
    """ Manage execution and scheduling of tasks. """

    def __init__(self, tasks, args, notifier, loop):
        self.tasks = tasks
        self.args = args
        self.notifier = notifier
        self.loop = loop
        self.workers_sem = asyncio.Semaphore(self.args.max_concurrency)
        self.wakeup = asyncio.Event(loop=loop)
        self.active = []
        self.history = collections.deque(maxlen=100)

    def is_active(self, task):
        """ Scan task exec list looking for this task. """
        for x in self.active:
            if x.task is task:
                return True
        return False

    @asyncio.coroutine
    def run(self):
        """ Babysit the task scheduling process. """
        while True:
            for task in self.tasks:
                if task.ready():
                    if not self.args.allow_overlap and self.is_active(task):
                        yield from self.notifier.warning('Skipping `%s`' %
                                                         task,
                                                         'Previous task is '
                                                         'still active.')
                    else:
                        yield from self.workers_sem.acquire()
                        yield from self.enqueue_task(task)
            try:
                yield from asyncio.wait_for(self.wakeup.wait(), 1)
            except asyncio.TimeoutError:
                pass
            else:
                self.wakeup.clear()

    @asyncio.coroutine
    def enqueue_task(self, task):
        """ Create (and return) the task status and run the task in the
        background. """
        context = TaskExecContext(task, self.loop)
        self.active.append(context)
        self.history.appendleft(context)
        f = self.loop.create_task(self.task_runner(context))
        f.add_done_callback(functools.partial(self.on_task_done, context))

    @asyncio.coroutine
    def task_runner(self, context):
        """ Background runner for actually executing the command. """
        if self.args.notify_exec:
            yield from self.notifier.info('Starting: `%s`' % context.task,
                                          footer='Exec #%d' % context.ident)
        yield from context.run_task()
        footer = 'Exec #%d - Duration %s' % (context.ident,
                                             context.elapsed)
        if context.returncode:
            yield from self.notifier.error('Failed: `%s`' % context.task,
                                           raw=context.output, footer=footer)
        elif self.args.notify_exec:
            yield from self.notifier.info('Succeeded: `%s`' % context.task,
                                          raw=context.output, footer=footer)
        for x in context.output.splitlines():
            print('[%s] [job:%d] [exit:%d] %s' % (context.task.cmd,
                  context.ident, context.returncode, x))

    def on_task_done(self, context, f):
        try:
            f.result()
        except Exception as e:
            traceback.print_exc()
            raise SystemExit("Unrecoverable Error: %s" % e)
        finally:
            self.active.remove(context)
            self.workers_sem.release()
            self.wakeup.set()
