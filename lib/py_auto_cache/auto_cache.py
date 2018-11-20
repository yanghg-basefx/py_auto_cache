# -*- coding: utf-8 -*-
import inspect
import time

try:
    import cPickle as pickle
except ImportError:
    import pickle
from .cache_wrapper import CacheWrapper
from .error import CacheMiss, DoNotCacheException

__all__ = [
    'get_auto_cache',
    'auto_cache_decorator',
    'DoNotCacheException',
]


class MG(object):
    """MG is a Module Global class used just for namespacing our module globals"""

    # _cache_dict is a global dict that is used to keep track of the AutoCache
    # objects that have been returned by the get_auto_cache function.
    _cache_dict = dict()


class AutoCache(CacheWrapper):
    """
    Gives us a convenient way to use a decorator to cache any function-call.

    It is a subclass of Cache, which implements the namespaced caching."""
    time_cost_suffix = 'time_cost'

    def __init__(self, namespace='default', default_expiry=None, wrapped_cache=None):
        """
        Sets up our cache with the given namespace.

        :param basestring namespace: Namespace to apply to our caches.
                                     None means use 'Default'.
        :param int default_expiry: expiry time (in seconds) to be used as the default for the set method.
                                   If no default is supplied in this initializer,
                                   an implementation-specific one will be provided by the caching engine.
        :param Cache wrapped_cache: cache instance which class must be subclassed of Cache.
                                    you can get some default implements in py_auto_cache.caches.*
                                    if you have other requirement,
                                    you can have your own implementation by inherit from Cache.
        """
        super(AutoCache, self).__init__(
            namespace=namespace,
            default_expiry=default_expiry,
            wrapped_cache=wrapped_cache,
        )
        self._time_cost_keys_pattern = self._add_monitoring_namespace_to_key(self.time_cost_suffix, '*')

        # wrappers_map is used to keep track of what real functions were mapped
        # to what wrappers in the decorator
        self._wrappers_map = {}

    def decorator(self, func):
        """
        A function decorator to wrap any other function in boilerplate code.

        It will cache the results of that function call (or read from cache, if
        available).

        To use it, do something like this:
        @<decorator>
        def function_name(...):
           ...

        Just use the function as usual after that, and it will be optimised with
        the cache.
        Note: you can call your function like this:
           function_name(..., update_auto_cache=True)
        to force it to evaluate the underlying function, and to update the
        cache again regardless of what is already in the cache.
        """

        def wrapper(*args, **kwargs):
            # We allow users to force the wrapper to ignore any pre-existing
            # cache entry if they pass in the arg update_auto_cache=True as an
            # argument
            try:
                if kwargs.pop('update_auto_cache', False):
                    raise CacheMiss(func, args, kwargs)  # pretend we there was a cache miss
                return self._read_cache(func, args, kwargs)
            except CacheMiss as e:
                return self._update_cache(e.func, e.args, e.kwargs)

        # When this decorator is applied to a function, we keep track of it so
        # we can access the original function later.
        self._wrappers_map[wrapper] = func
        return wrapper

    def set(self, key, value, expire_seconds=None, only_if_new=False, only_if_old=False, time_cost=0):
        """
        Set value in the cache corresponding to the given key.

        depending on how cache behaves given all the optional parameters.
        Maybe we should remove the expire_milliseconds option. It only adds
        confusion and isn't needed yet.

        :param basestring key: the key for the cached value
        :param basestring value: the value (must be a string) to be cached
        :param float expire_seconds: set an expire flag for key
        :param bool only_if_new: the set only happens if the key
                                 does NOT exist in the cache
        :param bool only_if_old: the set only happens if the key
                                 DOES exist in the cache
        :param float time_cost: how long when you calculate this value
        """

        self._wrapped_cache.set(self._add_monitoring_namespace_to_key(self.time_cost_suffix, key),
                                time_cost, expire_seconds, only_if_new, only_if_old)

        return super(AutoCache, self).set(key, value, expire_seconds, only_if_new, only_if_old)

    def time_cost_average(self):
        """
        Returns how much time was cost when the decorator was executing original function

        :return: average time cost
        :rtype: float
        """
        raw_keys = self._monitoring_keys_with_namespace(self.time_cost_suffix)
        if raw_keys:
            raw_values = self._wrapped_cache.multi_get(raw_keys)
        else:
            raw_values = []
        return _average([float(value) for value in raw_values if value is not None])

    def _get_source_func(self, wrapper):
        """
        Returns the raw function from the decorated one.

        Given the wrapper function that the decorator for this object has
        previously returned, this function returns the original function
        that was wrapped."""

        return self._wrappers_map[wrapper]

    def _get_cache_key(self, func, args, kwargs):
        """
        Compute the cache key to use for a function with its arguments.

        This is the function that's internally used to compute the key that's
        used to identify our cache location.  By default, it's combining the
        function name and a pickled version of the arguments, but you can
        override it in a sub-class if you can build a more efficient, but
        still unique, version.

        Its arguments are the original function that the decorator was applied
        to (available using _get_source_func) and the arguments that would be
        used in the call that is to be cached.

        The return type should be a unique string identifying that function
        call.

        :rtype: basestring
        """
        return '{mn}{sep}{func}{sep}{args}'.format(
            sep=self.sep,
            mn=inspect.getmodule(func).__name__,
            func=func.__name__,
            args=pickle.dumps([args, kwargs]),
        )

    def _update_cache(self, func, args, kwargs):
        """
        Executes the given function with given args and caches the result.

        This is ignoring the current state of the cache, ie it will evaluate
        the function even if the cache already has a value for it.

        It returns the result of the function evaluation.
        """

        try:
            start_time = time.time()
            value = func(*args, **kwargs)  # evaluate the function
            end_time = time.time()
            self.set(
                self._get_cache_key(func, args, kwargs),
                pickle.dumps(value),
                self._default_expiry,
                time_cost=end_time - start_time
            )  # cache the result
        except DoNotCacheException as e:
            # if the called function raised DoNotCacheException, then return
            # the value without caching
            return e.return_value
        return value

    def _read_cache(self, func, args, kwargs):
        """
        Strictly tries to get an already cached result.

        It returns None if the function call is not in the cache.
        """
        key = self._get_cache_key(func, args, kwargs)
        value_string = self.get(key)
        if value_string is None:
            raise CacheMiss(func, args, kwargs)  # pretend we there was a cache miss
        return pickle.loads(value_string)


def get_auto_cache(namespace='py_auto_cache', default_expiry=None, wrapped_cache=None):
    """
    This returns an AutoCache object for the given parameters.

    There will be exactly one such object returned for all calls to this
    function in the current process.
    """
    if (namespace, default_expiry, wrapped_cache) not in MG._cache_dict:
        MG._cache_dict[(namespace, default_expiry, wrapped_cache)] = AutoCache(
            namespace=namespace,
            default_expiry=default_expiry,
            wrapped_cache=wrapped_cache,
        )
    return MG._cache_dict[(namespace, default_expiry, wrapped_cache)]


def auto_cache_decorator(namespace='py_auto_cache',
                         default_expiry=None, wrapped_cache=None):
    """
    This returns a function that can be used to decorate a function with caching

    The decorator will be caching the results of the given function in a cache
    that is specific to the function and the absolute path to the file the
    function is in.

    For example:

    @auto_cache_decorator(host='localhost')
    def foo():
        sleep(60) # wait for a minute
        return 42

    foo()   # the first time this is called in a given pipeline will take 1
            # minute, after that, it will be quick, as it gets the result from
            # the cache

    WARNING: it will not account for any differences in execution environment
             that may affect the results of the function call. For instance,
             any functions called within the root function will be greatly
             affected by the sys.path.
    """
    return get_auto_cache(namespace, default_expiry, wrapped_cache).decorator


def _average(iterable):
    return (float(sum(iterable)) / len(iterable)) if iterable else 0
