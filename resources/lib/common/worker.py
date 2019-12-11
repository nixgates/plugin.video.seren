# -*- coding: utf-8 -*-
from resources.lib.common import tools

try:
    from Queue import Queue
    from Queue import Empty
except ImportError:
    from queue import Queue
    from queue import Empty

from threading import Thread


class Worker(Thread):
    def __init__(self, tasks, stop_flag=None):
        Thread.__init__(self)
        self.tasks = tasks
        self.stop_flag = stop_flag
        self.start()

    def run(self):
        while not self.tasks.empty():
            if tools.abortRequested or (self.stop_flag and self.stop_flag.isSet()):
                return

            try:
                func, args, kwargs = self.tasks.get(1)
            except Empty:
                return

            try:
                func(*args, **kwargs)
            except:
                import traceback
                traceback.print_exc()
            finally:
                self.tasks.task_done()


class ThreadPool:
    def __init__(self, stop_flag=None, workers=40):
        self.tasks = Queue(10 * workers)
        self.stop_flag = stop_flag
        self.results = []
        self.workers = []
        self.max_workers = workers

    def put(self, func, *args, **kwargs):
        self.tasks.put((func, args, kwargs))
        self.cleanup_workers()
        if len(self.workers) != self.max_workers:
            self.workers.append(Worker(self.tasks, self.stop_flag))

    def cleanup_workers(self):
        dead_workers = [i for i in self.workers if not i.isAlive()]

        for worker in dead_workers:
            try:
                self.workers.remove(worker)
            except:
                pass

    def map(self, func, args_list):
        for args in args_list:
            self.put(func, args)

    def terminate(self):
        [worker.stop() for worker in self.workers]

    def wait_completion(self):
        self.tasks.join()
