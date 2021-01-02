# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import datetime
import re
import time

from resources.lib.modules.globals import g


class IdentifyCreditsIntro:

    def __init__(self, title):
        self.title = title
        self.start_point = None
        self.end_point = None
        self._potential_starts = []
        self._potential_finishes = []
        self._sub_regex = re.compile(r'(\d+)\r\n(\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d)\r\n(.*)\r\n(.*)?')

    def identify_points(self, subtitle):
        # extract the sub file_path from the zip

        self._identify_start(subtitle['subcontents'])
        self._identify_finish(subtitle['subcontents'])

        self._potential_starts = sorted(self._potential_starts)
        self._potential_finishes = sorted(self._potential_finishes, reverse=True)

    def get_start(self):
        try:
            return self._potential_starts[0]
        except IndexError:
            return None

    def get_end(self):
        try:
            return self._potential_finishes[0]
        except IndexError:
            return None

    def _get_subtitles(self, subtitle):
        try:
            return {
                'subtitle': subtitle['MovieReleaseName'],
                'subcontents': self._sub_regex.findall(subtitle['Content'])
            }
        except IndexError:
            g.log('No available subtitles for item', 'debug')
            return None

    def _identify_finish(self, sub_points):
        sub_points.reverse()
        self._potential_finishes.append(self._convert_time_to_seconds(self._confirm_return_subpoint(sub_points)[1]))

    def _confirm_return_subpoint(self, sub_points):
        for point in sub_points:
            if not self._confirm_sub_point(point):
                continue
            return point

    def _identify_start(self, sub_points):
        self._potential_starts.append(self._convert_time_to_seconds(self._confirm_return_subpoint(sub_points)[1]))

    @staticmethod
    def _convert_time_to_seconds(time_stamp):
        x = time.strptime(time_stamp.split(',')[0], '%H:%M:%S')
        return datetime.timedelta(hours=x.tm_hour, minutes=x.tm_min, seconds=x.tm_sec).total_seconds()

    @staticmethod
    def _confirm_sub_point(sub_capture):
        if 'subtitle' in sub_capture[3].lower() or 'subtitle' in sub_capture[4].lower():
            return False
        return True
