import traceback

import xbmcgui

from resources.lib.modules.globals import g


class StackTraceException(Exception):
    def __init__(self, msg):
        tb = traceback.format_exc()
        g.log(msg if tb.startswith("NoneType: None") else f"{tb} \n{msg}", "error")


class UnsafeZipStructure(StackTraceException):
    pass


class InvalidMetaFormat(StackTraceException):
    pass


class FileIOError(StackTraceException):
    pass


class CannotGenerateRegexFilterException(StackTraceException):
    """Exception used when there is no valid input for generating the regex filters."""

    pass


class ActivitySyncFailure(StackTraceException):
    pass


class PreemptiveCancellation(Exception):
    pass


class UnsupportedProviderType(StackTraceException):
    pass


class FileIdentification(StackTraceException):
    def __init__(self, files):
        message = f"Failed to identify the correct file: \nFiles: {files}"
        super().__init__(message)


class UnexpectedResponse(StackTraceException):
    def __init__(self, api_response):
        message = f"API returned an unexpected response: \n{api_response}"
        super().__init__(message)


class DebridNotEnabled(StackTraceException):
    def __init__(self):
        g.log("Debrid Provider not enabled", "error")
        super().__init__("Debrid Provider not enabled")


class GeneralCachingFailure(StackTraceException):
    pass


class FailureAtRemoteParty(StackTraceException):
    def __init__(self, error):
        xbmcgui.Dialog().ok(
            g.ADDON_NAME,
            "There was an error at the remote party," " please check the log for more information",
        )
        g.log(f"Failure at remote party - {error}", "error")
        super().__init__(error)


class SkinNotFoundException(Exception):
    def __init__(self, skin_name):
        g.log(
            f'Unable to find skin "{skin_name}", check it\'s installed?',
            "error",
        )


class SkinInvalidException(Exception):
    def __init__(self, skin_name):
        g.log(
            f'"{skin_name}" Theme Folder Structure Invalid: Missing folder "Resources"',
            "error",
        )


class NormalizationFailure(StackTraceException):
    def __init__(self, details):
        super().__init__(f"NormalizationFailure: {details}")


class FileAlreadyExists(StackTraceException):
    pass


class TaskDoesNotExist(StackTraceException):
    pass


class GeneralIOError(StackTraceException):
    pass


class InvalidWebPath(StackTraceException):
    def __init__(self):
        super().__init__("Path does not start with http:// or https://")


class SourceNotAvailable(StackTraceException):
    def __init__(self):
        xbmcgui.Dialog().ok(g.ADDON_NAME, "This source is not available for instant downloading")


class KodiShutdownException(StackTraceException):
    pass


class InvalidSourceType(ValueError):
    def __init__(self, source_type):
        super().__init__(f"{source_type} sources are not available for download")


class ResolverFailure(StackTraceException):
    def __init__(self, source):
        super().__init__(f"Failure to resolve source:\n{source}")


class NoPlayableSourcesException(Exception):
    def __init__(self):
        g.log("No playable sources could be identified", "info")


class InvalidMediaTypeException(Exception):
    def __init__(self, media_type):
        super().__init__(f"Invalid media_type:\n{media_type}")


class UnsupportedCacheParamException(Exception):
    def __init__(self, parameter):
        super().__init__(f"Unsupported cache parameter:{parameter}")


class RanOnceAlready(RuntimeError):
    pass


class AuthFailure(RuntimeError):
    def __init__(self, message):
        super().__init__(message)
