# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import getopt
import gzip
import io
import json
import os
import re
import subprocess
import sys
import traceback
import zlib
from gzip import GzipFile

import requests
from requests.structures import CaseInsensitiveDict
from vcr.serialize import deserialize, serialize
from vcr.serializers import yamlserializer

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

PYTHON2 = True if sys.version_info.major == 2 else False

#####################################################################################################################
# SETUP DATA
#####################################################################################################################

SENSITIVE_STRINGS = BODY_SENSITIVE_STRINGS = [
    i for i in os.environ.get("SENSITIVE_STRINGS", "").split(",") if i
]
BODY_SENSITIVE_STRINGS += [
    os.environ.get("TRAKT_AUTH", "UnitTest"),
    os.environ.get(
        "TRAKT_CLIENT_ID",
        "4dd60d1ccb4b5c79aba64313467f6fefbda570605a927639549e8668558ce37e",
    ),
    os.environ.get("TVDB_JWT", "UnitTest"),
    os.environ.get("ALL_DEBRID_AUTH", "UnitTest"),
    os.environ.get("REAL_DEBRID_AUTH", "UnitTest"),
    os.environ.get("PREMIUMIZE_AUTH", "UnitTest"),
    os.environ.get("OMDB_API_KEY", "UnitTest"),
    os.environ.get("FANART_API_KEY", "UnitTest"),
    requests.get("https://api.ipify.org?format=json").json()["ip"],
]
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
CASSETTES_PATH = os.path.join(PROJECT_PATH, "tests", "cassettes")

#####################################################################################################################


def gzip_decompress(data):
    if PYTHON2:
        return GzipFile(fileobj=StringIO(data)).read()
    else:
        return gzip.decompress(data)


def gzip_compress(data):
    if PYTHON2:
        out = StringIO()
        with gzip.GzipFile(fileobj=out, mode="w") as f:
            f.write(data)
        return out.getvalue()
    else:
        return gzip.compress(data)


class VcrObject:
    def __init__(self, file_path, obj):
        self.request = obj[0]
        self.responses = [VcrResponse(i) for i in obj[1]]
        self.file_path = os.path.abspath(file_path)

    def to_dict(self):
        return {
            "requests": self.request,
            "responses": [i.to_dict() for i in self.responses],
        }


class VcrResponse:
    def __init__(self, response):
        self.response = response

    def to_dict(self):
        return self.response

    @property
    def headers(self):
        return CaseInsensitiveDict(self.response["headers"])

    @property
    def body(self):
        if self.is_compressed:
            return self._decompress_body(self.response["body"]["string"])
        else:
            return self.response["body"]["string"]

    @body.setter
    def body(self, value):
        if isinstance(value, dict):
            value = json.dumps(value).encode("utf-8")
        if self.is_compressed:
            self.response["body"]["string"] = self._compress_body(value)
        else:
            self.response["body"]["string"] = value

    def _decompress_body(self, value):
        if self.encoding == "gzip":
            return gzip_decompress(value)
        else:
            return zlib.decompress(value)

    def _compress_body(self, value):
        if self.encoding == "gzip":
            return gzip_compress(value)
        else:
            return zlib.compress(value)

    @property
    def is_json(self):
        return "application/json" in self.headers["content-type"]

    @property
    def encoding(self):
        return self.headers["content-encoding"][0]

    @property
    def is_compressed(self):
        encoding = self.headers.get("content-encoding", [])
        return encoding and encoding[0] in ("gzip", "deflate")


class CassetteCleaner:
    def __init__(self):
        self.sensitive_strings = SENSITIVE_STRINGS
        self.cassette_path = CASSETTES_PATH if os.path.exists(CASSETTES_PATH) else None
        self.silent = False
        self.responses_to_store = {}
        self.identified_strings = []
        self.identified_urls = []
        self.possible_ips = []
        self.files_to_process = []
        self.replacements_performed = 0
        self.censoring_types = [
            (
                self.identified_strings,
                "Sensitive Strings",
                self._identify_sensitive_strings_in_vcr_body,
            ),
            (self.identified_urls, "Sensitive URLS", self._identify_urls),
            (self.possible_ips, "Possible IPs", self._identify_ip_addresses),
        ]
        self.files = []

    @staticmethod
    def _extract_vcr_object(file_path):
        with open(file_path, "rb") as cassette:
            return VcrObject(file_path, deserialize(cassette.read(), yamlserializer))

    def _identify_sensitive_strings_in_vcr_body(self, vcr_object):
        items_found = False

        for response in vcr_object.responses:
            for i in self.sensitive_strings:
                strings = re.findall(re.escape(i).encode("utf-8"), response.body)
                if strings:
                    self.identified_strings += [(i, vcr_object)]

        return items_found

    def _identify_ip_addresses(self, vcr_object):
        for response in vcr_object.responses:
            ips = re.findall(br"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", response.body)
            if ips:
                self.possible_ips += [(ip, vcr_object) for ip in ips]

    def _identify_urls(self, vcr_object):
        for response in vcr_object.responses:
            urls = re.findall(
                br"https?:\\\\\/\\\\\/.*?(?:real-debrid|energycdn).*?(?:\\\\/[^,]*?)*(?=/.*?,)",
                response.body,
            )
            if urls:
                self.identified_urls += [(url, vcr_object) for url in urls]

    def _censor_body(self, vcr_object, string):
        for response in vcr_object.responses:
            string_sub = b"***SENSITIVE***"
            try:
                string = string.encode("utf-8")
            except:
                pass

            if string.startswith(b'"'):
                string_sub = b'"' + string_sub
            if string.endswith(b'"'):
                string_sub += b'"'

            if response.is_json:
                response.body, subs = self._censor_dict(
                    json.loads(response.body), string, string_sub
                )
            else:
                response.body, subs = re.subn(
                    re.escape(string), string_sub, response.body
                )
            self.replacements_performed += subs

    def _censor_dict(self, dict_, string, string_sub, subs=0):
        for k, v in dict_.items():
            if isinstance(v, dict):
                dict_[k], subs = self._censor_dict(v, string, string_sub, subs)
            elif isinstance(v, list):
                dict_[k], subs = self._censor_list(v, string, string_sub, subs)
            else:
                dict_[k], subs = self._censor_value(v, string, string_sub, subs)

        return dict_, subs

    def _censor_list(self, list_, string, string_sub, subs=0):
        for i in list_:
            if isinstance(i, dict):
                i, subs = self._censor_dict(i, string, string_sub, subs)
            elif isinstance(i, list):
                i, subs = self._censor_list(i, string, string_sub, subs)
            else:
                i, subs = self._censor_value(i, string, string_sub, subs)

        return list_, subs

    @staticmethod
    def _censor_value(value, string, string_sub, subs=0):
        if string.decode("utf-8") in str(value):
            subs += 1
            value = str(value).replace(
                string.decode("utf-8"), string_sub.decode("utf-8")
            )

        return value, subs

    def _output_response(self, vcr_object):
        self.print("Outputing file: {}".format(vcr_object.file_path))

        with io.open(vcr_object.file_path, "w+", encoding="utf-8") as output:
            output.write(serialize(vcr_object.to_dict(), yamlserializer))

    def _poll_for_censoring(self, items, item_type):
        if items:
            self.print("\n******************************************************")
            self.print("Found {} {}".format(len(items), item_type))
            for i in items:
                self.print("String: {}, File: {}".format(i[0], i[1].file_path))
            while True:
                try:
                    check = self.input("Would you like to censor these? 1=Yes, 0=No")
                    if (check and int(check)) or self.silent:
                        for i in items:
                            self._censor_body(i[1], i[0])
                            self.responses_to_store.update({i[1].file_path: i[1]})
                        break
                    else:
                        return
                except ValueError:
                    traceback.print_exc()
                    print("Bad Input...")

    def try_parse_commandline_arguments(self, argv):
        help_string = (
            "cassete_cleaner.py -d <sensitive_data> -c <cassete_path> -s <silent>"
        )
        try:
            opts, args = getopt.getopt(
                argv, "hd:c:s:", ["sensitive_data=", "cassete_path=", "silent="],
            )
        except getopt.GetoptError:
            print(help_string)
            sys.exit(2)
        for opt, arg in opts:
            if opt == "-h":
                print(help_string)
                sys.exit()
            elif opt in ("-d", "--sensitive_data"):
                self.sensitive_strings = arg
            elif opt in ("-c", "--cassete_path"):
                self.cassette_path = arg
            elif opt in ("-s", "--silent"):
                self.silent = bool(arg)

    def run(self, argv):
        self.try_parse_commandline_arguments(argv)
        if not self.sensitive_strings:
            self.sensitive_strings = self.input(
                "Please enter a comma separated list of strings to replace:"
            )

        self.files = [
            f
            for f in [os.path.abspath(i.strip()) for i in sys.stdin.readlines()]
            if f and f.endswith(".yaml") and os.path.isfile(f)
        ]

        if not self.cassette_path and not self.files:
            self.cassette_path = self.input(
                "Please provide the path to the cassette files:"
            )

        print("Identifying Files...")
        if self.files:
            [self.files_to_process.append(f) for f in self.files]
        else:
            self._walk_directory(self.cassette_path)
        print("Identified {} Files to check...".format(len(self.files_to_process)))
        print("Processing Files...")
        for file in self.files_to_process:
            self._perform_censoring_checks(file)

        for censor_type in self.censoring_types:
            self._poll_for_censoring(censor_type[0], censor_type[1])

        for response in self.responses_to_store.values():
            self._output_response(response)

        print(
            "Censored {} occurrences in {} files...".format(
                self.replacements_performed, len(self.responses_to_store)
            )
        )
        if len(self.responses_to_store) > 0:
            subprocess.call(
                "git add {}".format(" ".join(self.responses_to_store.keys())),
                shell=True,
            )

    def print(self, text):
        if not self.silent:
            print(text)

    def input(self, text):
        if not self.silent:
            return input(text)
        else:
            return None

    def _perform_censoring_checks(self, file_path):
        vcr_object = self._extract_vcr_object(file_path)
        for censor_type in self.censoring_types:
            censor_type[2](vcr_object)

    def _walk_directory(self, directory_path):
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            raise ValueError(
                "provided path does not exist or is not a directory: {}".format(
                    directory_path
                )
            )
        contents = os.listdir(directory_path)
        for path in contents:
            full_path = os.path.join(directory_path, path)
            if os.path.isdir(full_path):
                self._walk_directory(full_path)
            elif path.endswith(".yaml"):
                self.files_to_process.append(full_path)


if __name__ == "__main__":
    CassetteCleaner().run(sys.argv[1:])
