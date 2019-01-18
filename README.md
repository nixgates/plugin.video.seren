# Seren For Kodi - plugin.video.seren
Repository for Seren Development

This version of Seren may be unstable and may result in some undesired behavior. Use is at own risk

Change Log:

### Changelog 0.1.25
* Fixed setSetting argument naming (Fixes pre-emptive scraping)
* Trakt lists sorting now ignores 'The '
* Removed title appends to follow more closely to Kodi standards, another method of showing play percentage must be met
* Fixed Trakt dates for episode items
* Added Studio to metadata
* Seren now appends next season to current playlist during playback instead of after
* Removed references to now defunct OMNIConnect Addon
* Added Re-scrape cm item to episode items
* Fixed and optimised list pagination
* Trakt Lists now use user slugs to support users with periods in their username
* Added ability to direct search through plugin url
* Confirmed Trakt list sorting for all types except excluded (popularity, percentage, my rating)
* Added support to fail resolve if file ends with .rar
* Release titles are now deaccented and encoded with utf-8 to prevent unicode errors
* Fixed Ghost providers occuring if a provider was no longer available in a updated version of a provider package.
* Fixed TVDB module creating an artwork URL if no artwork is available
* Added token refresh lock to the TVDB module to stop instances of the class spawning mass refresh requests
* Massively reduced chance Kodi will drop Seren's settings
* Fixed Real Debrid post request making a get request after token refresh
* Custom Provider module now uses Zfile module to accomodate zipfile module bug on Android devices

### Version 0.1.24 Changelog:
* Fixed Movie Watchlist Sort to content type "Show"

### Version 0.1.23 Changelog:
* Added Watchlist sorting
* Added extra fallbacks for trakt outages
* Changed tools setSetting to a function so Kodi modules are not initialised if there is an exception

### Version 0.1.22 Changelog:
* Re-installation and updating of provider packages now honors previous settings
* Fixed Hidden items error if no connection to Trakt could be made.

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
