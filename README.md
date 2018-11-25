# Seren For Kodi - plugin.video.seren
Repository for Seren Development

This version of Seren may be unstable and may result in some undesired behavior. Use is at own risk

Change Log:

Version 0.1.09:
Increased torrent file identification
Extended timeout for failed cache assit attempts to 3 hours
Changed Trkat Scrobble Object to current playing item IMDB Number
Fixed Trakt Scrobbling with Up Next Addon Intergration
Fixed Trakt Scrobbling when seeking
Added increased fallbacks for TV show metadata

Version 0.1.08:
Restructed Settings page to use subsetting attribute
Added Support for Context Menu Addon

Version 0.1.07:
Added automatic migration from incorrect addon ID release
Added Notification if no sources are found during pre-scrape
Removed manual cache dialog prompt during pre-emptive scraping
Cache inserts now threaded
Added Semaphore to relieve thread pressure on database
Fixed KeyError exception in TVDB episode function
Custom Windows are now removed from scope with del
Removed Please Check Internet Connection Dialog
Added Logging for RD refresh Errors

Version 0.1.06:
Added 3D filter Setting
Added File Size Limit
Added View types for Seasons, Episodes and Default for Menus
Added Debrid Priorities
Added Install UpNext Addon Setting
Fixed capitalised Addon ID
Fixed issue where TVDB token was not initially created
Added ability to hide items from trakt manager
Adjusted Source Select to multiline string
Increased listitem size in custom source select window

Version 0.1.05:
Added better Hoster support
Changed hoster domains to (domain, name) tuple
Fixed issue where color change would set color even if cancelled
Cleaned up logging
Fixed Manual Caching
Adjusted Manual Caching display string
Fixed View Types not being set

