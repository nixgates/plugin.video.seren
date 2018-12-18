# Seren For Kodi - plugin.video.seren
Repository for Seren Development

This version of Seren may be unstable and may result in some undesired behavior. Use is at own risk

Change Log:


### Version 0.1.22 Changelog:
* Re-installation and updating of provider packages now honors previous settings
* Fixed Hidden items error if no connection to Trakt could be made.
* Added re-scrape context menu item (allows user to force cache refresh on scrape results)

### Version 0.1.21 Changelog:
* Added onAVStarted for Kodi 18+ due to issues with offset
* Re-factored code and cleaned up imports

### Version 0.1.20 Changelog:
* Provider installer re-write
* Provider packages can now update automatically or manually
* Fixed Trakt Movie Scrobbling
* Fixed Finish Watching Movies
* Added Remove (movie/episode) Progress to Trakt Manager

### Version 0.1.19 Changelog:
* Fixed Hidden Items (Possibly - please check)
* Trakt Lists now paginated and sorted
* Silent Scraper setting now reset on startup incase of Kodi crash
* New Shows and recently updated shows now filtered by Kodi Languge
* Corrected some typos
* Extended relevant show pack identification
* Un-aired episodes now removed from automatic playlist generator
* Premiumize autocache now runs premiumize cleanup instead of deleting transfer
* Added option to allow premiumize users to utilize transcoded files
* Added Banner image to episode objects
* Seasons now sorted by season number and not title
* Added basic duplicate provider filtering (provider name only)
* Show premiered dates now retrieved from Trakt and not TVDB

### Version 0.1.18 Changelog:
* Added fallback from TMDB SSL certificate issues

### Version 0.1.17 Changelog:
* Removed Trakt Lists pagination (Fixed List Sorting)
* Complete work over of TV show continue watching display
* Added Sort Options for Next Up
* Renamed and moved Continue Watching Menu items to "Finish Watching" and added to their respective folders
