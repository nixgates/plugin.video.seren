# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os
import re
import traceback

import polib
import requests


class LanguageAnalyzer(object):
    def __init__(self):
        self.all_codes = set()
        self.project_codes = set()
        self.language_codes = {}
        self.language_files = {}
        self.files_index = {}
        self.language_code_regex = re.compile(r'(?<![0-9a-zA-Z])([34][0-9]{4})(?![0-9a-zA-Z])')
        self.only_digits = re.compile(r'\D')
        self.replace_regex = "(?<![0-9a-zA-Z])({})(?![0-9a-zA-Z])"
        self.session = requests.Session()
        self.project_path = os.path.join(os.path.dirname(__file__), '../')

    def _index_languages(self):
        for root, dirs, files in os.walk(os.path.join(self.project_path, 'resources', 'language')):
            for f in files:
                if f.endswith('.po'):
                    self._index_language(os.path.join(root, f))

    def _index_language(self, file):
        lang = os.path.dirname(file).split('.')[-1]
        po = polib.pofile(file)
        codes = {int(self.only_digits.sub('', entry.msgctxt)) for entry in po}
        self.all_codes.update(codes)
        self.language_files[lang] = (file, po)
        self.language_codes[lang] = codes

    def _index_project(self):
        self.files_index = {}
        self.project_codes = set()
        self._walk_project(self._index_file)

    def _walk_project(self, func, **params):
        start = os.path.dirname(self.project_path)
        for root, dirs, files in os.walk(start):
            if '.idea' in root or \
                    '.git' in root or \
                    'tests' in root:
                continue
            for f in files:
                if not f.endswith('.py') and not f.endswith('.xml') \
                        or f == 'language.py' \
                        or f == 'test.py' \
                        or '.idea' in root \
                        or '.git' in root:
                    continue
                with io.open(os.path.join(root, f), 'r', encoding='utf8') as file:
                    func(f=f, file=file, root=root, start=start, **params)

    def _index_file(self, **params):
        root = params.pop('root')
        start = params.pop('start')
        file = params.pop('file')
        f = params.pop('f')
        relative_path = os.path.join(root.replace(start, ''), f)
        for idx, line in enumerate(file):
            for number in self.language_code_regex.findall(line):
                numeric = int(number)
                if numeric not in self.files_index:
                    self.files_index[numeric] = []
                self.files_index[numeric].append((relative_path, idx))
                self.project_codes.add(numeric)

    def _replace_occurrences(self, **params):
        root = params.pop('root')
        file = params.pop('file')
        f = params.pop('f')
        code_from = int(params.pop('code_from'))
        code_to = int(params.pop('code_to'))
        old_content = file.read()
        compiled_pattern = re.compile(self.replace_regex.format(code_from))
        if compiled_pattern.search(old_content):
            with io.open(os.path.join(root, f), 'w', encoding='utf8') as new_file:
                new_file.write(compiled_pattern.sub(str(code_to), old_content))

    def analyze_project(self):
        self._index_languages()
        self._index_project()

        for lang, codes in self.language_codes.items():
            print("Analyzing language: {}".format(lang))
            print("Missing these code: {}".format(self.project_codes - codes))
            print("Not used code: {}".format(codes - self.project_codes))
            print("Percent translated: {}".format(self.language_files[lang][1].percent_translated()))

        print("Duplicate entries found: {}".format(self._get_duplicates().keys()))
        print("Global not used in code: {}".format(self.all_codes - self.project_codes))
        print("Global available for use: {}".format(set(range(30000, max(self.all_codes) + 1)) - self.all_codes))

    def _get_duplicates(self):
        duplicates = {}
        for entry in self.language_files['en_gb'][1]:
            if entry.msgid in duplicates:
                duplicates[entry.msgid]['count'] += 1
                duplicates[entry.msgid]['duplicates'].append(int(self.only_digits.sub('', entry.msgctxt)))
            else:
                duplicates[entry.msgid] = {'count': 1,
                                           'first': int(self.only_digits.sub('', entry.msgctxt)),
                                           'duplicates': []}
        return {key: value for key, value in duplicates.items() if value['count'] > 1}

    def _remove_duplicates(self):
        duplicates = self._get_duplicates()
        duplicate_codes = {d for x in duplicates.values() for d in x['duplicates']}
        for lang, file in self.language_files.items():
            self._remove_not_used_entries(file[1], duplicate_codes)

        for d in duplicates.values():
            for x in d['duplicates']:
                self._walk_project(self._replace_occurrences, code_from=x, code_to=d['first'])

    def auto_translate_missing_entries(self):
        self._index_languages()
        try:
            for lang, po in self.language_files.items():
                for entry in po[1]:
                    if not entry.msgstr:
                        if lang.split('_')[0] == 'en':
                            entry.msgstr = entry.msgid
                        else:
                            entry.msgstr = self._try_get_translation(entry.msgid, lang.split('_')[0])
        except:
            traceback.print_exc()
            pass
        self._save_files()

    def clean_project(self):
        self._index_languages()
        self._index_project()

        for lang, codes in self.language_codes.items():
            print("Cleanup language: {}".format(lang))
            print("Adding missing codes: {}".format(str(self.project_codes - codes)))
            self._add_missing_entries(self.language_files[lang][1], self.project_codes - codes)
            print("Removing Not used code: {}".format(str(codes - self.project_codes)))
            self._remove_not_used_entries(self.language_files[lang][1], codes - self.project_codes)

        print("Removing duplicates")
        self._remove_duplicates()
        self._save_files()

    def order_codes(self):
        self._index_languages()
        self._index_project()

        sorted_codes = sorted(self.project_codes)
        for code_to in range(30000, 30000 + len(self.project_codes)):
            code_from = sorted_codes.pop(0)
            self._change_po_lang_code(code_from, code_to)
            self._walk_project(self._replace_occurrences, code_from=code_from, code_to=code_to)

        self._save_files()

    def _save_files(self):
        self._update_occurrences()
        [po.sort(key=lambda x: x.msgctxt) for file, po in self.language_files.values()]
        [po.save(file) for file, po in self.language_files.values()]

    @staticmethod
    def _missing_numbers(num_list):
        original_list = [x for x in range(num_list[0], num_list[-1] + 1)]
        num_list = set(num_list)
        return list(num_list ^ set(original_list))

    def _update_occurrences(self):
        self._index_project()
        for lang, codes in self.language_codes.items():
            for entry in self.language_files[lang][1]:
                entry.occurrences = self.files_index.get(int(self.only_digits.sub('', entry.msgctxt)))

    def _add_missing_entries(self, po, codes):
        for entry in self.language_files['en_gb'][1]:
            if any(str(c) in entry.msgctxt for c in codes):
                entry.msgstr = ''
                po.append(entry)

    @staticmethod
    def _remove_not_used_entries(po, codes):
        to_remove = [entry for entry in po if any(str(c) in entry.msgctxt for c in codes)]
        [po.remove(entry) for entry in to_remove]

    def _change_po_lang_code(self, code_from, code_to):
        for lang, codes in self.language_codes.items():
            for entry in self.language_files[lang][1]:
                if str(code_from) in str(entry.msgctxt):
                    entry.msgctxt = entry.msgctxt.replace(str(code_from), str(code_to))

    def _try_get_translation(self, value, lang):
        data = self.session.get(
            "https://api.mymemory.translated.net/get",
            params={
                "q": value,
                "langpair": "en|{}".format(lang),
                "de": "xxxxxx@protonmail.com"}).json()
        if 'MYMEMORY' in data['responseData']['translatedText']:
            raise Exception(data['responseData']['translatedText'])

        matches = data['matches']
        for match in sorted(matches, key=lambda x: x['match'], reverse=True):
            if match['segment'] in value:
                return value.replace(match['segment'], match['translation'])
        return value


if __name__ == "__main__":
    analyzer = LanguageAnalyzer()
    analyzer.analyze_project()
    analyzer.clean_project()
    analyzer.order_codes()
    analyzer.auto_translate_missing_entries()
