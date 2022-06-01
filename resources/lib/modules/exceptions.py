# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import traceback

import xbmcgui

from resources.lib.modules.globals import g


class StackTraceException(Exception):
    def __init__(self, msg):
        tb = traceback.format_exc()
        g.log("{} \n{}".format(tb, msg) if not tb.startswith("NoneType: None") else msg, "error")


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
        message = "Failed to identify the correct file: \nFiles: {}".format(files)
        super(FileIdentification, self).__init__(message)


class UnexpectedResponse(StackTraceException):
    def __init__(self, api_response):
        message = "API returned an unexpected response: \n{}".format(api_response)
        super(UnexpectedResponse, self).__init__(message)


class DebridNotEnabled(StackTraceException):
    def __init__(self):
        g.log("Debrid Provider not enabled", "error")
        super(DebridNotEnabled, self).__init__("Debrid Provider not enabled")


class GeneralCachingFailure(StackTraceException):
    pass


class FailureAtRemoteParty(StackTraceException):
    def __init__(self, error):
        xbmcgui.Dialog().ok(
            g.ADDON_NAME,
            "There was an error at the remote party,"
            " please check the log for more information",
        )
        g.log("Failure at remote party - {}".format(error), "error")
        super(FailureAtRemoteParty, self).__init__(error)


class SkinNotFoundException(Exception):
    def __init__(self, skin_name):
        g.log(
            'Unable to find skin "{}", check it\'s installed?'.format(skin_name),
            "error",
        )


class NormalizationFailure(StackTraceException):
    def __init__(self, details):
        super(NormalizationFailure, self).__init__(
            "NormalizationFailure: {}".format(details)
        )


class FileAlreadyExists(StackTraceException):
    pass


class TaskDoesNotExist(StackTraceException):
    pass


class GeneralIOError(StackTraceException):
    pass


class InvalidWebPath(StackTraceException):
    pass


class SourceNotAvailable(StackTraceException):
    def __init__(self):
        xbmcgui.Dialog().ok(
            g.ADDON_NAME, "This source is not available for instant downloading"
        )


class KodiShutdownException(StackTraceException):
    pass


class InvalidSourceType(ValueError):
    def __init__(self, source_type):
        xbmcgui.Dialog().ok(
            g.ADDON_NAME,
            "Sorry, {} type sources are not available for downloading".format(
                source_type
            ),
        )
        super(InvalidSourceType, self).__init__(
            "{} sources are not available for download".format(source_type)
        )


class ResolverFailure(StackTraceException):
    def __init__(self, source):
        super(ResolverFailure, self).__init__(
            "Failure to resolve source:\n{}".format(source)
        )


class NoPlayableSourcesException(Exception):
    def __init__(self):
        g.log(
            "No playable sources could be identified",
            "info"
        )


class InvalidMediaTypeException(Exception):
    def __init__(self, media_type):
        super(InvalidMediaTypeException, self).__init__(
            "Invalid media_type:\n{}".format(media_type)
        )


class UnsupportedCacheParamException(Exception):
    def __init__(self, parameter):
        super(UnsupportedCacheParamException, self).__init__(
            "Unsupported cache parameter:{}".format(parameter)
        )


class RanOnceAlready(RuntimeError):
    pass
