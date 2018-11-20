# -*- coding: utf-8 -*-
"""
Created by yanghg at 18-5-7 上午11:21
"""


class CacheError(Exception):
    """
    Base class for all errors
    """


class HostError(CacheError):
    """
    Be raised if the host is invalid
    """


class AutoCacheError(CacheError):
    """
    Base class for auto cache errors
    """


class CacheMiss(AutoCacheError):
    """
    Raised whenever we tried to find a key that's not in the cache.
    """

    def __init__(self, func, args, kwargs):
        super(CacheMiss, self).__init__()

        self.func = func
        self.args = args
        self.kwargs = kwargs


class DoNotCacheException(AutoCacheError):
    """
    Tells the cache mechanism to not store the result in the cache.

    Instead of a regular return call, a function that's being cached
    can raise a DoNotCacheException (which is given the return value),
    signalling to the cache framework that the return value should not
    be cached. Subsequent calls to the function will still miss the
    cache, and a new value can be computed and returned (and possibly
    cached).
    """

    def __init__(self, return_value):
        """
        Populates the DoNotCacheException with the given return_value.
        """
        super(DoNotCacheException, self).__init__()

        self.return_value = return_value
