# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import base64

from resources.lib.modules.globals import g


class MessageServer:

    """
    Handles messaging between python interpreters
    """

    def __init__(self, index_id, prefix):
        self._base_prefix = "SEREN_MESSAGING_"
        self._win = g.HOME_WINDOW
        self._index_id = index_id
        self._index = []
        self._prefix = "{}_{}".format(self._base_prefix, prefix)
        self._fetch_index()

    def _fetch_index(self):
        index = self._get_property(self._index_id)
        if index:
            index_value = self._get_property(index)
            self._index = index_value.split("|") if index_value else []

    def _get_property(self, message_id):
        value = self._win.getProperty(self._prefix + message_id)
        if not value:
            return None
        return base64.b64decode(value).decode("utf-8")

    def _clear_message(self, message_id):
        self._win.clearProperty(self._base_prefix + message_id)
        self._index.remove(message_id)
        self._update_window_index()

    def _set_property(self, message_id, value):
        self._win.setProperty(
            self._prefix + message_id, base64.b64encode(value.encode("utf-8"))
        )

    def clear_message(self, message_ids):
        """
        Clears the given message from the message queue
        :param message_ids: ID of message
        :type message_ids: str
        :return: None
        :rtype: None
        """
        if isinstance(message_ids, list):
            [self._clear_message(i) for i in self._index]
        else:
            self._clear_message(message_ids)

    def get_messages(self):
        """
        Fetch awaiting messages
        :return: List of message tuples (msg_id, message)
        :rtype: list
        """
        self._fetch_index()
        messages = [(i, self._get_property(i)) for i in self._index if i]
        return messages

    def _update_window_index(self):
        self._set_property(self._index_id, "|".join(self._index))

    def _add_message_to_index(self, message_id):
        self._fetch_index()
        self._index.append(message_id)
        self._update_window_index()

    def send_message(self, message):
        """
        Method to push a message
        :param message: Stringable message to send
        :type message: str
        :return: None
        :rtype: None
        """
        message_id = str(hash(self._index_id + str(message)))
        self._set_property(message_id, message)
        self._add_message_to_index(message_id)
