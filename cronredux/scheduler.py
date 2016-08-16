"""
Handle task monitoring and scheduling.
"""

import asyncio
import datetime
import functools
import resource
import shellish
import subprocess
import time
import traceback
from concurrent import futures


class Task(object):
    """ Encapsulate a repeated task. """

    def __init__(self, crontab, cmd):
        self.crontab = crontab
        self.cmd = cmd
        self.last_eta = crontab.next()
        self.run_count = 0
        self.elapsed = 0
        self.cpu_time = 0
        self.last_status = None

    def __str__(self):
        return '<Task: cmd="%s">' % self.cmd

    def __call__(self):
        start = time.perf_counter()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        ps = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              universal_newlines=True)
        output, _ = ps.communicate()
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        elapsed = time.perf_counter() - start
        cpu_time = after.ru_utime - before.ru_utime
        cpu_time += after.ru_stime - before.ru_stime
        self.run_count += 1
        self.elapsed += elapsed
        self.cpu_time += cpu_time
        return {
            "returncode": ps.returncode,
            "output": output,
            "cputime": cpu_time,
            "elapsed": elapsed,
        }


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
        self.wakeup = asyncio.Event(loop=loop)

    @asyncio.coroutine
    def run(self):
        """ Babysit the task scheduling process. """
        while True:
            for task in self.tasks:
                done = [x for x in self.active[task] if x.done()]
                for x in done:
                    self.active[task].remove(x)
            for task in self.tasks:
                eta = task.crontab.next()
                # look for rollover as our exec trigger.
                if eta > task.last_eta:
                    if self.active[task] and not self.args.allow_overlap:
                        self.notifier.warning('Skipping `%s`' % task,
                                              'Previous task is still active.')
                    else:
                        self.enqueue_task(task)
                task.last_eta = eta
            try:
                yield from asyncio.wait_for(self.wakeup.wait(), 1)
            except asyncio.TimeoutError:
                pass
            else:
                self.wakeup.clear()

    def enqueue_task(self, task):
        """ Submit a task to the executor (thread pool). """
        f = self.loop.run_in_executor(self.executor, self.run_task, task)
        self.active[task].append(f)
        return f

    def run_task(self, task):
        """ Run process from an Executor context.  NOTE: This runs from a
        different thread than the event loop! """
        try:
            self._run_task(task)
        except Exception as e:
            shellish.vtmlprint("<red>Unhandled Exception: %s</red>" % e)
            traceback.print_exc()

    def _run_task(self, task):
        job_id = task.run_count  # save for threadsafety
        if self.args.notify_exec:
            fn = functools.partial(self.notifier.info, 'Starting: `%s`' % task,
                                   footer='Job #%d' % job_id)
            self.loop.call_soon_threadsafe(fn)
        status = task()
        took = datetime.timedelta(seconds=status['elapsed'])
        footer = 'Job #%d - Duration %s' % (job_id, took)
        if status['returncode']:
            title = 'Error: `%s`' % task
            fn = functools.partial(self.notifier.error, title,
                                   raw=status['output'], footer=footer)
            self.loop.call_soon_threadsafe(fn)
            rc = 'error(%d)' % status['returncode']
        else:
            title = 'Completed: `%s`' % task
            if self.args.notify_exec:
                fn = functools.partial(self.notifier.info, title,
                                       raw=status['output'], footer=footer)
                self.loop.call_soon_threadsafe(fn)
            rc = 'ok'
        for x in status['output'].splitlines():
            print('[%s] [%d] [%s] %s' % (task.cmd, job_id, rc, x))
        self.loop.call_soon_threadsafe(self.wakeup.set)
