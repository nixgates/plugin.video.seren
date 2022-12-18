import time


class TimeLogger:
    def __init__(self, action):
        self.action = action
        self.start = None

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.log(f"Processing Time - {(time.time() - self.start) * 1000.0:6.0f}ms - {self.action}")

    @staticmethod
    def log(msg):
        print(f"SEREN: {msg}")


def stopwatch(func):
    def decorated(*args, **kwargs):
        method_class = args[0]
        action = f"{method_class.__class__.__name__}.{func.__name__}"
        # for item in args[1:]:
        #     action += u".{}".format(item)
        with TimeLogger(action):
            return func(*args, **kwargs)

    return decorated
