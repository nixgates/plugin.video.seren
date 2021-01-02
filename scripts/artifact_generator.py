# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals, print_function

import os
import zipfile

from resources.lib.common import tools

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree


class ArtifactGenerator:
    def __init__(self):
        self.base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.artifact_path = os.path.join(self.base_path, "artifact")
        tools.makedirs(self.artifact_path, exist_ok=True)

    def create_zip(self):
        xml = ElementTree.parse(os.path.join(self.base_path, "addon.xml"))
        addon = xml.find(".")
        addon_id = addon.attrib["id"]
        version = addon.attrib["version"]
        git_sha = self.read_all_text(os.path.join(self.base_path, ".gitsha")) or "local"

        final_zip = os.path.join(
            self.artifact_path, "{0}-{1}-{2}.zip".format(addon_id, version, git_sha)
        )

        print("Creating zip for: {0} v.{1} - {2}".format(addon_id, version, git_sha))
        zip_file = zipfile.ZipFile(final_zip, "w", compression=zipfile.ZIP_DEFLATED)
        root_len = len(os.path.dirname(self.base_path))

        ignore = [
            ".git",
            ".github",
            ".gitignore",
            ".DS_Store",
            "thumbs.db",
            ".idea",
            "venv",
            ".pylintrc",
            ".gitlab-ci.yml",
            ".idea",
            "venv",
            ".pytest_cache",
            "mock_kodi",
            "tests",
            "scripts",
            "__pycache__",
            ".pyo",
            ".pyc",
            "test.py",
            "artifact",
        ]

        for root, dirs, files in os.walk(self.base_path):
            # remove any unneeded git artifacts
            for i in ignore:
                if i in dirs:
                    try:
                        dirs.remove(i)
                    except:
                        pass
                for f in files:
                    if f.startswith(i) or f.endswith(i):
                        try:
                            files.remove(f)
                        except:
                            pass

            archive_root = os.path.abspath(root)[root_len:]

            for f in files:
                full_path = os.path.join(root, f)
                archive_name = os.path.join(archive_root, f)
                zip_file.write(full_path, archive_name, zipfile.ZIP_DEFLATED)

        zip_file.close()

    @staticmethod
    def read_all_text(file_path):
        try:
            with open(file_path, "r") as f:
                return f.read()
        except IOError:
            return None


if __name__ == "__main__":
    artifact_generator = ArtifactGenerator()
    artifact_generator.create_zip()
