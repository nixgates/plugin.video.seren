# -*- coding: utf-8 -*-
import os
import re
import time
import io
from resources.lib.common import tools


class LanguageAnalyzer(object):
    def __init__(self):
        self.all_codes = set()
        self.project_codes = set()
        self.language_codes = {}
        self.language_code_regex = re.compile(r'[34]\d{4}')

    def _walk_languages(self):
        for root, dirs, files in os.walk(os.path.join(os.path.dirname(__file__), 'resources', 'language')):
            for f in files:
                if f.endswith('.po'):
                    self._index_language(os.path.join(root, f))

    def _index_language(self, file):
        lang = os.path.dirname(file).split('.')[-1]
        with io.open(file, 'r', encoding='utf-8') as language_file:
            codes = set([int(i) for i in self.language_code_regex.findall(language_file.read())])

        self.all_codes.update(codes)
        self.language_codes[lang] = codes

    def _walk_project(self):
        for root, dirs, files in os.walk(os.path.dirname(__file__)):
            for f in files:
                if not f.endswith('.py') and not f.endswith('.xml'):
                    continue
                with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                    self.project_codes.update(set([int(i) for i in self.language_code_regex.findall(file.read())]))
        pass

    def analyze(self):
        self._walk_languages()
        self._walk_project()
        for lang, codes in self.language_codes.items():
            print("Analyzing language: {}".format(lang))
            print("Missing these code: {}".format(str(self.all_codes - codes)))
            print("Not used code: {}".format(str(codes - self.all_codes)))

        print("Global not used in code: {}".format(str(self.all_codes - self.project_codes)))
        print("Global available for use: {}".format(str(set(range(32000, max(self.all_codes)+1)) - self.all_codes)))


if __name__ == "__main__":
    start = time.time()
    analyzer = LanguageAnalyzer()
    analyzer.analyze()
    tools.log('Processing Time - %s' % (time.time() - start))
