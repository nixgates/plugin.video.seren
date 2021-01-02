# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import time


class TimeLogger:
    def __init__(self, action):
        self.action = action
        self.start = None

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log(
            "Processing Time - {:6.0f}ms - {}".format(
                (time.time() - self.start) * 1000.0, self.action
            )
        )

    @staticmethod
    def log(msg):
        print("SEREN: {}".format(msg))


def stopwatch(func):
    def decorated(*args, **kwargs):
        method_class = args[0]
        action = "{}.{}".format(method_class.__class__.__name__, func.__name__)
        # for item in args[1:]:
        #     action += u".{}".format(item)
        with TimeLogger(action):
            return func(*args, **kwargs)

    return decorated
