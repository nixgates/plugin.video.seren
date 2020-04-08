import requests
import re
import time
import datetime
import gzip

from resources.lib.indexers.opensubs import OpenSubsApi
from resources.lib.common import tools

class IdentifyCreditsIntro:

    def __init__(self, title):
        self.title = title
        self.start_point = None
        self.end_point = None
        self.os_api = OpenSubsApi()
        self._potential_starts = []
        self._potential_finishes = []
        self.identify_points()

    def identify_points(self):
        # extract the sub file from the zip
        subs = self._get_subtitles()
        if not subs:
            return None

        for sub in subs:
            self._identify_start(sub['subcontents'])
            self._identify_finish(sub['subcontents'])

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

    def _get_subtitles(self):
        try:
            subs = self.os_api.search(self.title)
            subs = [i for i in subs if i['SubLanguageID'] == 'eng']
            sub_files = []
            sub_regex = re.compile(r'(\d+)\r\n(\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d)\r\n(.*)\r\n(.*)?')

            sub = subs[0]
            unzipped = requests.get(sub['SubDownloadLink']).content
            
            try:
                from StringIO import StringIO
                unzipped = gzip.GzipFile(fileobj=StringIO(unzipped)).read().decode('utf-8')
            except ImportError:
                import io
                unzipped = gzip.decompress(unzipped).decode('utf-8')
            new_sub = {
                'subtitle': sub['MovieReleaseName'],
                'subcontents': sub_regex.findall(unzipped)
            }
            sub_files.append(new_sub)

        except IndexError:
            tools.log('No available subtitles for item', 'debug')
            return None
        except IOError:
            tools.log('Unable to obtain sub file due to robot filtering', 'notification')
            return None
        except requests.exceptions.ConnectionError:
            tools.log('Failed to connect to OpenSubs', 'error')
            return None

        return sub_files

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
