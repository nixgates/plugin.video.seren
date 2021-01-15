# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import threading

from resources.lib.common import tools
from resources.lib.modules.globals import g

try:
    from Queue import Queue
    from Queue import Empty
    from Queue import Full
except ImportError:
    from queue import Queue
    from queue import Empty
    from queue import Full

from threading import Thread


class ClearableQueue(Queue):
    """A custom queue subclass that provides a method."""

    def clear(self):
        """Clears all items from the queue."""

        with self.mutex:
            unfinished = self.unfinished_tasks - len(self.queue)
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError("task_done() called too many times")
                self.all_tasks_done.notify_all()
            self.unfinished_tasks = unfinished
            self.queue.clear()
            self.not_full.notify_all()


class ThreadPoolWorker(Thread):
    """Worker thread that handles the execution of the consumes tasks from the main queue."""

    def __init__(self, tasks, exception_handler, stop_flag=None):
        Thread.__init__(self)
        self.exception_handler = exception_handler
        self.tasks = tasks
        self.stop_flag = stop_flag
        self.start()

    def run(self):
        """
        Executes the workload
        :return:
        :rtype:
        """
        while not self.tasks.empty() and not self.stop_flag.is_set():

            try:
                func, result_callback, args, kwargs = self.tasks.get(timeout=0.1)
                self.name = str(func)
                result_callback(func(*args, **kwargs))
            except Empty:
                break
            except BaseException as ex:
                g.log_stacktrace()
                self.exception_handler(ex)
                break
            finally:
                try:
                    self.tasks.task_done()
                except ValueError:
                    pass


class ThreadPool:

    """
    Helper class to simplify raising workers
    """

    def __init__(self, workers=40):
        self.limiter = g.get_global_setting("threadpool.limiter") == "true"
        self.tasks = ClearableQueue(2 * workers)
        self.stop_event = threading.Event()
        self.results = None
        self.workers = []
        self.max_workers = 1 if self.limiter else workers
        self.exception = None
        self.result_threading_lock = threading.Lock()

    def _handle_result(self, result):
        self.result_threading_lock.acquire()
        try:
            if result is not None:
                if isinstance(result, dict):
                    if self.results is None:
                        self.results = {}
                    tools.smart_merge_dictionary(self.results, result)
                elif isinstance(result, (list, set)):
                    if self.results is None:
                        self.results = []
                    if isinstance(result, list):
                        self.results.extend(result)
                    else:
                        self.results.append(result)
                else:
                    if self.results is None:
                        self.results = []
                    self.results.append(result)
        finally:
            self.result_threading_lock.release()

    def put(self, func, *args, **kwargs):
        """
        Adds task to queue and sets thread child to process task
        :param func: method to run in task
        :type func: object
        :param args: arguments to assign to method
        :type args: any
        :param kwargs: kwargs to assign to method
        :type kwargs: any
        :return:
        :rtype:
        """
        if self.exception:
            return

        while True:
            try:
                self.tasks.put((func, self._handle_result, args, kwargs), timeout=0.01)
                break
            except Full:
                if self.exception:
                    return

        self._worker_maintenance()

    def _worker_maintenance(self):
        self._cleanup_workers()
        if len(self.workers) != self.max_workers:
            self.workers.append(
                ThreadPoolWorker(self.tasks, self.exception_handler, self.stop_event,)
            )

    def _cleanup_workers(self):
        [
            self._safe_remove_worker(worker)
            for worker in [i for i in self.workers if not i.is_alive()]
        ]

    def _safe_remove_worker(self, worker):
        try:
            self.workers.remove(worker)
        except ValueError:
            pass


    def map(self, func, args_list):
        """
        Maps arguments to the specified func
        :param func: method to use against arguments
        :type func: object
        :param args_list: List of arguments, each ran against the supplied method
        :type args_list: iterable
        :return:
        :rtype:
        """
        [self.put(func, args) for args in args_list]

    def exception_handler(self, exception):
        """
        Terminates all threads and sets ThreadPool exception
        :param exception:
        :type exception: class
        :return:
        """
        self.terminate()
        self.exception = exception

    def terminate(self):
        """
        Sets stop event for threads and clears current tasks
        :return:
        """
        if not self.stop_event.is_set():
            self.stop_event.set()
        self.tasks.clear()

    def wait_completion(self):
        """
        Joins threads and waits for their completion, raises any exceptions if any present and returns results if
        present
        :return:
        :rtype:
        """
        self._try_raise()
        self._worker_maintenance()
        [i.join() for i in self.workers]
        self._try_raise()

        try:
            return self.results
        finally:
            self.results = None

    def _try_raise(self):
        if self.exception:
            g.log_stacktrace()
            raise self.exception  # pylint: disable-msg=E0702
