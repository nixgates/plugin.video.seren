# Seren For Kodi - plugin.video.seren
Repository for Seren Development

This version of Seren may be unstable and may result in some undesired behavior. Use is at own risk

Change Log:

### Version 0.1.16 Changelog:
* Fixed season items not being marked as watched
* Added try/except clauses to catch errors with get_hidden_items
* Adjust Info detection to better detect source information
* Added fallback if info list was empty for Source Select
* Added ability to show sources in source select as a single line in case of skins that do not support the multiline view
* Simplified provider failure output
* Added removal of unknown video keys for Kodi 18
* Removed trakt list lengths
* Premiumize module now removes items from account if it failed to resolve a link
* Premiumize cleanup now occurs at end of resolving
* Threads no longer marked as daemon as it doesn't work within Kodi
* Forced provider threads to return if getSources canceled
* Added fallback for gathering of hoster domains

### Version 0.1.15 Changelog:
* Fallback for DateTime ValueError
* Changed process of list generating so window shouldn't contain random number of items

### Version 0.1.14 Changelog:
* Increased Trakt Caching

### Version 0.1.13 Changelog:
* Source Select items now clickable
* Esc Key now closes Source Select dialog

### Version 0.1.12 Changelog:
* Added premiumize transfer database cleanup to maintenance script
* Changed scrobble ID back to Trakt as IMDB ID was unreliable causing trakt progress for some random show called pride
* if the IMDB ID wasn't available for an episode (sorry for my testers watching origin)
* Fixed issue with keepalive not dying causing scrobble issues and issues with Upnext
* Added 265 priority sort
* Some spelling mistakes
* Changed Upnext episode IDs to Trakt ID
* Added setUniqueIDs to tools.addDirectoryItem function
* Hide Item in trakt manager now actually sends the trakt request (Bad nix)

### Version 0.1.11 Changelog:
* Added workaround for Kodi 18 Widgets
* Increased support for Kodi 18 player
* Fixed issue with Kodi 18 where pre-emptive scraping wouldn't occur
* Adjusted menu content types so they now respect their content correctly

### Version 0.1.10 Changelog:
* Adjusted Migration Script so it no longer broke Super Faviorates
* Adjusted TMDB movie artwork to fix issue where it would display the wrong media (removed thumbnail)

### Version 0.1.09 Changelog:
* Increased torrent file identification
* Extended timeout for failed cache assit attempts to 3 hours
* Changed Trkat Scrobble Object to current playing item IMDB Number
* Fixed Trakt Scrobbling with Up Next Addon Intergration
* Fixed Trakt Scrobbling when seeking
* Added increased fallbacks for TV show metadata

### Version 0.1.08:
* Restructed Settings page to use subsetting attribute
* Added Support for Context Menu Addon

### Version 0.1.07:
* Added automatic migration from incorrect addon ID release
* Added Notification if no sources are found during pre-scrape
* Removed manual cache dialog prompt during pre-emptive scraping
* Cache inserts now threaded
* Added Semaphore to relieve thread pressure on database
* Fixed KeyError exception in TVDB episode function
* Custom Windows are now removed from scope with del
* Removed Please Check Internet Connection Dialog
* Added Logging for RD refresh Errors

### Version 0.1.06:
* Added 3D filter Setting
* Added File Size Limit
* Added View types for Seasons, Episodes and Default for Menus
* Added Debrid Priorities
* Added Install UpNext Addon Setting
* Fixed capitalised Addon ID
* Fixed issue where TVDB token was not initially created
* Added ability to hide items from trakt manager
* Adjusted Source Select to multiline string
* Increased listitem size in custom source select window

### Version 0.1.05:
* Added better Hoster support
* Changed hoster domains to (domain, name) tuple
* Fixed issue where color change would set color even if cancelled
* Cleaned up logging
* Fixed Manual Caching
* Adjusted Manual Caching display string
* Fixed View Types not being set

