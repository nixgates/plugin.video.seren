import requests
import inspect
import os

from resources.lib.common import tools

allow_provider_requests = True
_provider_path = os.path.join(tools.dataPath, 'providers')
_provider_modules_path = os.path.join(tools.dataPath, 'providerModules')

class PreemptiveCancellation(Exception):
    pass

def _monkey_check(method):

    def do_method(*args, **kwargs):

        global allow_provider_requests
        if not allow_provider_requests and\
                any([True for i in inspect.stack() if i[1].startswith(_provider_path)]) and\
                any([True for i in inspect.stack() if i[1].startswith(_provider_path)]):
                raise PreemptiveCancellation

        return method(*args, **kwargs)

    return do_method

# Monkey patch the common requests calls

requests.get = _monkey_check(requests.get)
requests.post = _monkey_check(requests.post)
requests.head = _monkey_check(requests.head)
requests.delete = _monkey_check(requests.delete)
requests.put = _monkey_check(requests.put)

requests.Session.get = _monkey_check(requests.Session.get)
requests.Session.post = _monkey_check(requests.Session.post)
requests.Session.head = _monkey_check(requests.Session.head)
requests.Session.delete = _monkey_check(requests.Session.delete)
requests.Session.put = _monkey_check(requests.Session.put)

