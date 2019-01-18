# Custom Providers

## Developing Custom Providers

### Meta File
Each provider package **must** supply a meta.json file and all entries must be present.

An example meta:

    {
	    "remote_meta": "https://yourdomain.com/meta.json",
	    "version": "1.1.1",
	    "update_directory": "https://yourdomain.com/ftp/",
	    "name": "ExamplePackage",
	    "author": "Example"
    }

 - **version**: full stop seperated version number
 - **name**: Name of provider package this must match exactly in your folder structure and update directories
 - **author**: Author Alias
 - **update_directory**: Your update directory is the url to the folder that contains your release versions, Seren will automatically generate the final file name based on your meta contents ie: "https://yourdomain.com/ftp/ExamplePackage-1.1.1.zip. Your release zip files must resemble this format include the dash to separate version number and package name.
 - **remote_meta**: This remote file is used by seren to identify currently release version information and if the update_directory has been changed. This means Seren can still identify and install updates in the event you change your update location.

 **NOTE**: your remote_meta information is updated alongside a package update. This means remote_meta locations will change according to the meta information in your release so please be sure your remote meta file url is correct with each release or you will break your users updates.

### Install Zip Structure
Custom providers have very specific folder structures that must be maintained.
The contents of the install zip file should follow this format exactly

	    meta.json
		providers
			|
			package name
				|
				language code
				init.py
					|
					provider type
					init.py
						|
						(provider.pys)
						init.py
		providerModules
			|
			package name
				|
				init.py
				(extra modules for your providers)

### Language init.py
The init file in each language folder your provider package supports must supply a list of provider file names for each applicable provider type.

An example init contents is provided below:

    # -*- coding: utf-8 -*-

	import hosters
	import torrent

	def get_hosters():
	    return hosters.__all__

	def get_torrent():
	    return torrent.__all__

### Example Provider Types

All providers must return a list of dictionary objects as their final result.

##### Torrent Provider

    import re
    import requests

	class sources:

	    def __init__(self):
	      self.domain = ""
		  self.base_link = ""
		  self.search_link = ""

		    def movie(self, title, year):

		        return torrent_list

		    def episode(self, simpleInfo, allInfo):

		        return torrent_list

Torrent entry points should return a list torrent dict objects.

Example torrent object:

     {
	     'release_title' = <string>,
	     'magnet' = <string>,
	     **'hash' = <string>,
	     **'quality' = <string>,
	     **'info' = <list of string values>
	     'size' = <int>,
			     |	Size of source in megabytes
	     'seeds' = <int>,
	     'package' = <string>,
			     |	Package Type (single, season, show)
	}

** Denotes optional return values. If these values are not present Seren will attempt to generate the values based on the release title of the source.

#### Hoster Provider
Hoster providers will always start at their respective function and end at the sources function

The sources function must return a list of dictionary objects

	class source:
	    def __init__(self):
	        self.priority = 1
			self.language = ['en']
	        self.domains = ['']
	        self.base_link = ''
			self.search_link = ''

	  def movie(self, imdb, title, localtitle, aliases, year):

	            return results

	   def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):

	            return results

	   def episode(self, url, imdb, tvdb, title, premiered, season, episode):

	            return results

	   def sources(self, url, hostDict, hostprDict):

	            return sources

	    def resolve(self, url):
	        return url

Example Dictionary Object:

    {
	    'source': <string>,
	    'quality': <string>,
			    |
	    'language': <string>,
			    | Language Code
	    'url': <string>,
	    'direct': <boolean>,
	    'debridonly': <boolean>
	    'info': <list of string values>
    }
