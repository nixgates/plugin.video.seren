import os
import sys
import subprocess
import xml.etree.cElementTree as ET
from xml.dom import minidom
import xbmc
import xbmcgui
import re

__author__ = 'Team Kodi <http://kodi.tv>'
__credits__ = 'Team Kodi'
__date__ = 'Sat Oct 24 10:35:33 BST 2015'
__platform__ = 'ALL'
__version__ = '2.23.0'


class Addon(object):
    def __init__(self, id=None):
        self._id = id
        self._config = None
        self._strings = {}
        self._settings = {}

        # Parse the addon config
        try:
            filepath = os.path.join(os.getcwd(), 'addon.xml')
            xml = ET.parse(filepath)
            self._config = xml.getroot()
            self._id = self.getAddonInfo("id") or id
        except ET.ParseError:
            pass
        except IOError:
            pass

        # Load in english strings
        langfile = os.path.join(os.getcwd(), 'resources', 'language', 'resource.language.en_gb', 'strings.po')
        if os.path.isfile(langfile):
            regex = re.compile(r'msgctxt "#(.*?)"\s*msgid "(.*?)"', re.MULTILINE)
            langfile = open(langfile, 'r').readlines()
            langfile = ''.join(langfile)
            po = re.findall(regex, langfile)
            for key, value in po:
                self._strings.update({key: value})
        else:
            # Fall back to xml version
            langfile = os.path.splitext(langfile)[0] + '.xml'
            if os.path.isfile(langfile):
                xml = ET.parse(langfile)
                root = xml.getroot()
                strings = root.findall("string")

                for node in strings:
                    id = node.attrib["id"]
                    text = node.text
                    self._strings[id] = text

        # Load settings
        settings_root = os.path.join(os.getcwd(), 'resources', 'settings.xml')
        settings_user = xbmc.translatePath(os.path.join(self.getAddonInfo("profile"), 'settings.xml'))
        if not os.path.isfile(settings_user):
            if os.path.isfile(settings_root):
                xml = ET.parse(settings_root)
                settings = xml.findall(".//setting")

                for node in settings:
                    if "id" in node.attrib:
                        id = node.attrib["id"]
                        default = ""
                        if "default" in node.attrib:
                            default = node.attrib["default"]
                        self._settings[id] = default
                self._savesettings()
        else:
            xml = ET.parse(settings_user)
            settings = xml.findall("./setting")

            for node in settings:
                if "id" in node.attrib:
                    id = node.attrib["id"]
                    value = ""
                    if "value" in node.attrib:
                        value = node.attrib["value"]
                    self._settings[id] = value

    def _savesettings(self):
        "Save the current settings to the user profile directory. NOTE: not an official api method"
        settings_dir = xbmc.translatePath(self.getAddonInfo("profile"))
        if not os.path.isdir(settings_dir):
            os.makedirs(settings_dir)
        settings_file = os.path.join(settings_dir, "settings.xml")

        root = ET.Element("settings")
        for key, value in self._settings.iteritems():
            node = ET.Element("setting")
            node.attrib["id"] = key
            node.attrib["value"] = value
            root.append(node)

        # Format the xml and write out to the settings file
        formatted_xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent="\t")
        f = open(settings_file, "w")
        f.write(formatted_xml.encode('utf-8'))
        f.close()

    def getAddonInfo(self, key):
        properties = ['author', 'changelog', 'description', 'disclaimer',
                      'fanart', 'icon', 'id', 'name', 'path', 'profile',
                      'stars', 'summary', 'type', 'version']
        if key not in properties:
            raise ValueError('%s is not a valid property.' % key)
        if key == "profile":
            return 'special://profile/addon_data/{0}/'.format(self._id)
        if key == "path":
            return 'special://home/addons/{0}'.format(self._id)
        if self._config and key in self._config.attrib:
            return self._config.attrib[key]
        return ""

    def getLocalizedString(self, key):
        key = str(key)
        if key in self._strings:
            return self._strings[key]
        return ""

    def getSetting(self, key):
        if key in self._settings:
            return self._settings[key]
        return ""

    def openSettings(self):
        settings_file = xbmc.translatePath(os.path.join(self.getAddonInfo("profile"), "settings.xml"))
        if os.path.isfile(settings_file):
            if sys.platform.startswith('linux'):
                subprocess.Popen(["gedit", settings_file])
            else:
                subprocess.Popen(["notepad", settings_file])
            return
        xbmcgui.Dialog().ok("XBMC", "Unable to find settings file")

    def setSetting(self, key, value):
        self._settings[key] = value
        self._savesettings()  # Save change to the settings file immediately
