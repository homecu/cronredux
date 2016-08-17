"""
Handle task monitoring and scheduling.
"""

import asyncio
import datetime
import shellish
import subprocess
import time
import traceback


class Task(object):
    """ Encapsulate a repeated task. """

    def __init__(self, crontab, cmd):
        self.crontab = crontab
        self.cmd = cmd
        self.last_eta = crontab.next()
        self.run_count = 0
        self.elapsed = 0
        self.last_status = None

    def __str__(self):
        return '<Task: cmd="%s">' % self.cmd

    @asyncio.coroutine
    def __call__(self, loop):
        start = time.perf_counter()
        ps = yield from asyncio.create_subprocess_shell(self.cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, loop=loop)
        output, _ = yield from ps.communicate()
        assert _ is None
        elapsed = time.perf_counter() - start
        self.run_count += 1
        self.elapsed += elapsed
        self.last_status = status = {
            "returncode": ps.returncode,
            "output": output.decode(),
            "elapsed": elapsed,
        }
        return status


class Scheduler(object):
    """ Manage execution and scheduling of tasks. """

    def __init__(self, tasks, args, notifier, loop):
        self.tasks = tasks
        self.args = args
        self.notifier = notifier
        self.loop = loop
        self.active = dict((x, []) for x in tasks)
        self.workers_sem = asyncio.Semaphore(self.args.max_concurrency)
        self.wakeup = asyncio.Event(loop=loop)

    @asyncio.coroutine
    def run(self):
        """ Babysit the task scheduling process. """
        while True:
            for task in self.tasks:
                eta = task.crontab.next()
                # look for rollover as our exec trigger.
                if eta > task.last_eta:
                    if self.active[task] and not self.args.allow_overlap:
                        yield from self.notifier.warning('Skipping `%s`' %
                                                         task,
                                                        'Previous task is '
                                                        'still active.')
                    else:
                        yield from self.workers_sem.acquire()
                        self.loop.create_task(self.run_task(task))
                task.last_eta = eta
            try:
                yield from asyncio.wait_for(self.wakeup.wait(), 1)
            except asyncio.TimeoutError:
                pass
            else:
                self.wakeup.clear()

    @asyncio.coroutine
    def run_task(self, task):
        job_id = task.run_count
        self.active[task].append(job_id)
        try:
            yield from self._run_task(task)
        except Exception as e:
            shellish.vtmlprint("<red>Unhandled Exception: %s</red>" % e)
            traceback.print_exc()
        finally:
            self.active[task].remove(job_id)
            self.workers_sem.release()
            self.wakeup.set()

    @asyncio.coroutine
    def _run_task(self, task):
        job_id = task.run_count  # save for threadsafety
        if self.args.notify_exec:
            yield from self.notifier.info('Starting: `%s`' % task,
                                          footer='Job #%d' % job_id)
        status = yield from task(self.loop)
        took = datetime.timedelta(seconds=status['elapsed'])
        footer = 'Job #%d - Duration %s' % (job_id, took)
        if status['returncode']:
            yield from self.notifier.error('Error: `%s`' % task,
                                           raw=status['output'], footer=footer)
        elif self.args.notify_exec:
            yield from self.notifier.info('Completed: `%s`' % task,
                                          raw=status['output'], footer=footer)
        for x in status['output'].splitlines():
            print('[%s] [job:%d] [exit:%d] %s' % (task.cmd, job_id,
                  status['returncode'], x))
