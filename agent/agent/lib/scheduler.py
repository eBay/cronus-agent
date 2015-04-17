#pylint: disable=C0103, W0212, W0703, W0201, W0232,W0105
'''
Copyright 2014 eBay Software Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
'''
copied from http://www.razorvine.net/download/kronos.py
Module that provides a cron-like task scheduler
'''

import sys
import sched
import weakref
import threading
import time
import traceback

import logging
from agent.lib.thread_pool import ThreadPool

LOG = logging.getLogger(__name__)

THREADPOOL = ThreadPool(50)

class Scheduler:
    '''The Scheduler itself.'''

    def __init__(self):
        self.running = True
        self.sched = sched.scheduler(time.time, self.__delayfunc)

    def __delayfunc(self, delay):
        '''
        This delay function is basically a time.sleep() that is
        divided up, so that we can check the self.running flag while delaying.
        there is an additional check in here to ensure that the top item of
        the queue hasn't changed
        '''
        if delay < 10:
            time.sleep(delay)
        else:
            toptime = self._getqueuetoptime()
            endtime = time.time() + delay
            period = 5
            stoptime = endtime - period
            while self.running and stoptime > time.time() and \
                self._getqueuetoptime() == toptime:
                time.sleep(period)
            if not self.running or self._getqueuetoptime() != toptime:
                return
            now = time.time()
            if endtime > now:
                time.sleep(endtime - now)

    def _acquire_lock(self):
        ''' acquire lock '''
        pass

    def _release_lock(self):
        ''' release lock '''
        pass

    def add_interval_task(self, action, taskname, initialdelay, interval, args, kw):
        '''Add a new Interval Task to the schedule.'''
        if initialdelay < 0:
            raise ValueError("Delay must be >0")
        if interval < 1:
            raise ValueError("interval must be >=1")
        # Select the correct IntervalTask class. Not all types may be available!
        TaskClass = ThreadedIntervalTask
        if not args:
            args = []
        if not kw:
            kw = {}
        task = TaskClass(taskname, interval, action, args, kw)
        LOG.debug("scheduled %s: interval %f" % (taskname, interval))
        self.schedule_task(task, initialdelay)
        return task

    def schedule_task(self, task, delay):
        '''Add a new task to the scheduler with the given delay (seconds).

        Low-level method for internal use.

        '''
        if self.running:
            # lock the sched queue, if needed
            self._acquire_lock()
            try:
                task.event = self.sched.enter(delay, 0, task,
                            (weakref.ref(self),))
            finally:
                self._release_lock()

    def start(self):
        '''Start the scheduler.'''
        self._run()

    def stop(self):
        '''Remove all pending tasks and stop the Scheduler.'''
        self.running = False
        self._clearschedqueue()

    def cancel(self, task):
        '''Cancel given scheduled task.'''
        task.isCanceled = True
        try:
            self.sched.cancel(task.event)
        except BaseException:
            pass

    def _getqueuetoptime(self):
        ''' get time of the fist in queue'''
        return self.sched._queue[0].time

    def _clearschedqueue(self):
        ''' clear queue '''
        self.sched._queue[:] = []

    def _run(self):
        ''' Low-level run method to do the actual scheduling loop. '''
        while self.running:
            try:
                self.sched.run()
            except Exception as ex:
                LOG.error("ERROR DURING SCHEDULER EXECUTION %s" % ex)
                LOG.error("".join(traceback.format_exception(*sys.exc_info())))
                LOG.error("-" * 20)
            # queue is empty; sleep a short while before checking again
            if self.running:
                time.sleep(5)


class Task:
    '''Abstract base class of all scheduler tasks'''

    def __init__(self, name, action, args, kw):
        '''This is an abstract class!'''
        self.name = name
        self.action = action
        self.args = args
        self.kw = kw
        self.isCanceled = False

    def __call__(self, schedulerref):
        '''Execute the task action in the scheduler's thread.'''
        try:
            self.execute()
        except Exception as ex:
            self.handle_exception(ex)
        self.reschedule(schedulerref())

    def reschedule(self, scheduler):
        '''This method should be defined in one of the sub classes!'''
        raise NotImplementedError("You're using the abstract base class 'Task',"
            " use a concrete class instead")

    def execute(self):
        '''Execute the actual task.'''
        self.action(*self.args, **self.kw)

    def handle_exception(self, exc):
        '''Handle any exception that occured during task execution.'''
        LOG.error("ERROR DURING TASK EXECUTION %s" % exc)
        LOG.error("".join(traceback.format_exception(*sys.exc_info())))
        LOG.error("-" * 20)

class IntervalTask(Task):
    '''A repeated task that occurs at certain intervals (in seconds).'''

    def __init__(self, name, interval, action, args = None, kw = None):
        Task.__init__(self, name, action, args, kw)
        self.interval = interval

    def reschedule(self, scheduler):
        '''Reschedule this task according to its interval (in seconds).'''
        if not self.isCanceled:
            scheduler.schedule_task(self, self.interval)

class ThreadedScheduler(Scheduler):
    '''A Scheduler that runs in its own thread.'''

    def __init__(self):
        ''' constructor '''
        Scheduler.__init__(self)
        # we require a lock around the task queue
        self._lock = threading.Lock()

    def start(self):
        '''Splice off a thread in which the scheduler will run.'''
        LOG.debug("starting threadedScheduler")
        self.running = True

        self.thread = threading.Thread(target = self._run)
        self.thread.setDaemon(True)
        self.thread.start()

    def stop(self):
        '''Stop the scheduler and wait for the thread to finish.'''
        LOG.debug("stopping threadedScheduler")
        Scheduler.stop(self)
        try:
            self.thread.join()
        except AttributeError:
            pass

    def _acquire_lock(self):
        '''Lock the thread's task queue.'''
        self._lock.acquire()

    def _release_lock(self):
        '''Release the lock on th ethread's task queue.'''
        self._lock.release()


class ThreadedTaskMixin:
    '''A mixin class to make a Task execute in a separate thread.'''

    def __call__(self, schedulerref):
        '''Execute the task action in its own thread.'''
#        threading.Thread(target = self.threadedcall).start()
        THREADPOOL.addTask(self.threadedcall)
        self.reschedule(schedulerref())

    def threadedcall(self):
        '''
        This method is run within its own thread, so we have to
        do the execute() call and exception handling here.
        '''
        try:
            self.execute()
        except Exception as ex:
            self.handle_exception(ex)

class ThreadedIntervalTask(ThreadedTaskMixin, IntervalTask):
    '''Interval Task that executes in its own thread.'''
    pass
