# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import json

import xbmc

from resources.lib.common.thread_pool import ThreadPool
from resources.lib.modules.globals import g
from resources.lib.modules.messages import MessageServer
from resources.lib.modules.providers import CustomProviders


class ProvidersServiceManager(CustomProviders, ThreadPool, MessageServer):
    """
    Handles messaging to provider package services
    """

    def __init__(self):
        super(ProvidersServiceManager, self).__init__()
        ThreadPool.__init__(self)
        MessageServer.__init__(self, 'SERVICE_MANAGER_INDEX', 'SERVICE_MANAGER')
        self.poll_database()
        self._registered_services = {}
        self._message_types = {
            'shutdown': self._shutdown_package_services,
            'startup': self._start_remote_services,
        }

    def run_long_life_manager(self):
        """
        Starts background messaging server
        :return: None
        :rtype: None
        """
        g.log('Starting Service Manager Long Life Service')
        [self._start_package_services(package) for package in self.known_packages]
        self._service_trigger_loop()

    def _service_trigger_loop(self):
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            xbmc.sleep(500)
            self._handle_messages(self.get_messages())

    def _shutdown_package_services(self, package_name):
        g.log('Request to shutdown services for package: {}'.format(package_name))
        services = self._registered_services.get(package_name, {}).values()
        for service in services:
            service['shutdown_method'](service['config'])
            service['running'] = False
        self._registered_services.pop(package_name, None)

    def _start_remote_services(self, package_name):
        self._start_package_services(self.get_single_package(package_name))

    @staticmethod
    def _run_service(service_info):
        # We only allow 5 failures in a service script before we stop trying to run the script.
        count = 0
        monitor = xbmc.Monitor()
        while not monitor.abortRequested() and count < 5:
            count += 1
            service_info['run_method'](service_info['config'])

        service_info['running'] = False

    def _start_package_services(self, package):
        g.log('Request to start services for package: {}'.format(package['pack_name']))
        for service in package['services'].split('|'):
            if not service:
                continue
            module = __import__('providers.{}.{}'.format(package['pack_name'], service[:-2]), fromlist=[str('')])
            if hasattr(module, 'run_service'):
                self._register_and_config_service(service, module, package)

        self._start_registered_services()

    def _register_and_config_service(self, service_name, module, package):
        self._registered_services.update({
            package['pack_name']: {
                service_name: {
                    'package_name': package['pack_name'],
                    'service_name': service_name,
                    'run_method': module.run_service,
                    'shutdown_method': getattr(module, 'shutdown_service', lambda a: None),
                    'config': getattr(module, 'pre_config', lambda: None)(),
                    'running': False
                }
            }
        })

    def _start_registered_services(self):
        for package in self._registered_services.values():
            for service in package.values():
                if not service['running']:
                    self.put(self._run_service, service)
                else:
                    g.log('Attempt to start an already running service - {}.{}'.format(service['package_name'],
                                                                                       service['service_name']))

    def _handle_messages(self, messages):
        if not messages:
            return
        for message in messages:
            if message[1]:
                value = json.loads(message[1])
                self._message_types[value['message_type']](value['package_name'])
            self.clear_message(message[0])

    def start_package_services(self, package_name):
        """
        Starts services for given package
        :param package_name: name of package
        :type package_name: str
        :return: None
        :rtype: None
        """
        self._send_service_message("startup", package_name)

    def stop_package_services(self, package_name):
        """
        Sends shutdown request to package services
        :param package_name: name of package
        :type package_name: str
        :return: None
        :rtype: None
        """
        self._send_service_message("shutdown", package_name)

    def _send_service_message(self, message_type, package_name):
        self.send_message(json.dumps({"message_type": message_type, "package_name": package_name}))
