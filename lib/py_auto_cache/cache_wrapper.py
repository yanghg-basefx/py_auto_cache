# -*- coding: utf-8 -*-
from logging import getLogger, StreamHandler
from .error import HostError
from .cache import Cache

from .caches import DictCache as DefaultCache

logger = getLogger('py_auto_cache')
logger.addHandler(StreamHandler())

__all__ = ['CacheWrapper']


class CacheWrapper(object):
    """
    A wrapper class for cache server to help support namespaces.

    The methods in this class will, unless otherwise stated,
    work within the namespace defined by this class.
    """
    global_ns = 'py_auto_cache'
    sep = ':'

    cache_prefix = 'cache'
    monitoring_prefix = 'monitoring'

    hits_suffix = 'hits'
    misses_suffix = 'misses'

    def __init__(self, namespace='default', default_expiry=None, wrapped_cache=None):
        """
        Sets up our cache with the given namespace.

        :param basestring namespace: Namespace to apply to our interactions
                                     with cache. None means use 'Default'.
        :param int default_expiry: expiry time (in seconds) to be used as the default for the set method.
                                   If no default is supplied in this initializer,
                                   an implementation-specific one will be provided by the caching engine.
        :param Cache wrapped_cache: cache instance which class must be subclassed of Cache.
                                    you can get some default implements in py_auto_cache.caches.*
                                    if you have other requirement,
                                    you can have your own implementation by inherit from Cache.
        """
        super(CacheWrapper, self).__init__()
        assert namespace != 'default', 'namespace must be assigned'
        if wrapped_cache is None:
            wrapped_cache = DefaultCache()
        assert isinstance(wrapped_cache, Cache), 'wrapped_cache must be instance of CacheProxy'

        self._namespace = namespace
        self._default_expiry = default_expiry
        self._wrapped_cache = wrapped_cache

        self._namespace_prefix = {}
        self._namespace_suffix = {}

        self._misses_key = self._add_monitoring_namespace_to_key(self.misses_suffix, '*')
        self._hits_key = self._add_monitoring_namespace_to_key(self.hits_suffix, '*')

    def get(self, key):
        """
        Get value corresponding to the given key, from the cache.

        Returns None if there is no match.

        :param basestring key: the key for the cached value
        :return: value saved in cache server.
        """
        key = self._add_cache_namespace_to_key(key)
        value = self._wrapped_cache.get(key)
        if value is None:
            self._wrapped_cache.increase(self._misses_key)
        else:
            self._wrapped_cache.increase(self._hits_key)
        return value

    def set(self, key, value, expire_seconds=None, only_if_new=False, only_if_old=False):
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
        """
        return self._wrapped_cache.set(self._add_cache_namespace_to_key(key), value,
                                       self._default_expiry if expire_seconds is None else expire_seconds,
                                       only_if_new, only_if_old)

    def hits(self):
        """
        Returns how many times you hit cache successfully by using CacheWrapper.get

        :return: the number of hit times
        :rtype: int
        """
        return int(self._wrapped_cache.get(self._hits_key) or 0)

    def misses(self):
        """
        Returns how many times you hit cache unsuccessfully by using CacheWrapper.get

        :return: the number of misses times
        :rtype: int
        """
        return int(self._wrapped_cache.get(self._misses_key) or 0)

    def hit_rate(self):
        """
        Returns the hit rate by using CacheWrapper.get

        hit rate means: hits / (hits + misses)

        :return: hit rate
        :rtype: float
        """
        hits = self.hits()
        misses = self.misses()
        count = hits + misses
        if count == 0:
            return 0
        return float(hits) / (hits + misses)

    def memory_size(self):
        """
        Returns the number of bytes being consumed in the cache by data in this namespace.
        The returned value might be an approximation.

        :return: the number of bytes
        :rtype: int
        """
        raw_keys = self._cache_keys_with_namespace()
        return self._wrapped_cache.memory_size(raw_keys)

    def get_keys(self, pattern='*'):
        """
        Get cleaned up keys (the namespace this class adds will be stripped)
        in the cache.

        It searches for keys by pattern
        (which will have the namespace implicitly added).

        - ? matches one character
        - * matches non or many characters
        - [] matches one specific characters like regexp
        - \ escapes special characters.

        :param basestring pattern: a pattern string,
                                   the namespace will be implicitly added.
        :return: a list of matched keys without namespace prefix.
        """
        return [self._remove_cache_namespace_from_key(name)
                for name in self._cache_keys_with_namespace(pattern)]

    def delete(self, *keys):
        """
        Delete all entries that match the given keys from the
        wrapped cache.

        This method will delete keys from all the alternate hosts, too.

        :param keys: a list of keys (not patterns)
        """
        raw_keys = [self._add_cache_namespace_to_key(key) for key in keys]
        self._wrapped_cache.delete(raw_keys)

    def clear(self):
        """
        Clear all the keys from all the servers in this namespace.

        This will match keys from all the server, then delete them.
        """
        self._wrapped_cache.clear(self._add_cache_namespace_to_key('*'))

    def _get_full_prefix(self, prefix):
        """
        'monitoring' -> py_auto_cache:namespace:'monitoring':

        :param prefix: short prefix like 'monitoring'
        :return: full prefix like py_auto_cache:namespace:'monitoring':
        """
        if prefix not in self._namespace_prefix:
            self._namespace_prefix[prefix] = '{global_ns}{sep}{ns}{sep}{prefix}{sep}'.format(sep=self.sep,
                                                                                             global_ns=self.global_ns,
                                                                                             prefix=prefix,
                                                                                             ns=self._namespace)
        return self._namespace_prefix[prefix]

    def _get_full_suffix(self, suffix):
        """
        'hits' -> :'hits'

        :param suffix: short suffix like 'hits'
        :return: long suffix like :'hits'
        """
        if suffix not in self._namespace_suffix:
            self._namespace_suffix[suffix] = '{sep}{suffix}'.format(sep=self.sep, suffix=suffix)
        return self._namespace_suffix[suffix]

    def _add_namespace_to_key(self, key, prefix=None, suffix=None):
        """
        ('key', 'monitoring', 'hits') -> py_auto_cache:namespace:'monitoring':'key':'hits'

        :param key: original key like 'key'
        :param prefix: short prefix like 'monitoring'
        :param suffix: short suffix like 'hits'
        :return: key with namespace like py_auto_cache:namespace:'monitoring':'key':'hits'
        """
        return '{prefix}{key}{suffix}'.format(prefix=self._get_full_prefix(prefix), key=key,
                                              suffix=self._get_full_suffix(suffix))

    def _remove_namespace_from_key(self, key, prefix=None, suffix=None):
        """
        py_auto_cache:namespace:'monitoring':'key':'hits' -> 'key'

        :param key: key with namespace like py_auto_cache:namespace:'monitoring':'key':'hits'
        :param prefix: short prefix like 'monitoring'
        :param suffix: short suffix like 'hits'
        :return: original key like 'key'
        """
        return _remove_suffix(_remove_prefix(key, self._get_full_prefix(prefix)),
                              self._get_full_suffix(suffix))

    def _keys_with_namespace(self, pattern='*', prefix=None, suffix=None):
        """
        ('*', 'monitoring', 'hits') -> [py_auto_cache:namespace:'monitoring':'key1':'hits',
                                        py_auto_cache:namespace:'monitoring':'key2':'hits',
                                        py_auto_cache:namespace:'monitoring':'key3':'hits',
                                        ...]

        :param pattern: pattern string like '*'
        :param prefix: short prefix like 'monitoring'
        :param suffix: short suffix like 'hits'
        :return: a list of matched keys with namespace like [py_auto_cache:namespace:'monitoring':'key1':'hits',
                                                             py_auto_cache:namespace:'monitoring':'key2':'hits',
                                                             py_auto_cache:namespace:'monitoring':'key3':'hits',
                                                             ...]

        """
        return self._wrapped_cache.get_keys(self._add_namespace_to_key(pattern, prefix, suffix))

    def _add_cache_namespace_to_key(self, key):
        """
        'key' -> py_auto_cache:namespace:'cache':'key':None

        :param key: original cache key like 'key'
        :return: cache key with namespace like py_auto_cache:namespace:'cache':'key':None
        """
        return self._add_namespace_to_key(key, self.cache_prefix)

    def _remove_cache_namespace_from_key(self, key):
        """
        py_auto_cache:namespace:'cache':'key':None -> 'key'

        :param key: cache key with namespace like py_auto_cache:namespace:'cache':'key':None
        :return: original cache key like 'key'
        """
        return self._remove_namespace_from_key(key, self.cache_prefix)

    def _cache_keys_with_namespace(self, pattern='*'):
        """
        '*' -> [py_auto_cache:namespace:'cache':'key1':None,
                py_auto_cache:namespace:'cache':'key2':None,
                py_auto_cache:namespace:'cache':'key3':None,
                ...]

        :param pattern: pattern string like '*'
        :return: a list of matched keys with cache namespace like [py_auto_cache:namespace:'cache':'key1':None,
                                                                   py_auto_cache:namespace:'cache':'key2':None,
                                                                   py_auto_cache:namespace:'cache':'key3':None,
                                                                   ...]
        """
        return self._keys_with_namespace(pattern, self.cache_prefix)

    def _add_monitoring_namespace_to_key(self, suffix, key):
        """
        ('hits', 'key') -> py_auto_cache:namespace:'monitoring':'key':'hits'

        :param suffix: short monitoring suffix like 'hits'
        :param key: original monitoring key like 'key'
        :return: monitoring key with namespace like py_auto_cache:namespace:'monitoring':'key':'hits'
        """
        return self._add_namespace_to_key(key, self.monitoring_prefix, suffix)

    def _remove_monitoring_namespace_from_key(self, suffix, key):
        """
        py_auto_cache:namespace:'monitoring':'key':'hits' -> 'key'

        :param suffix: short monitoring suffix like 'hits'
        :param key:  monitoring key with namespace like py_auto_cache:namespace:'monitoring':'key':'hits'
        :return: original monitoring key like 'key'
        """
        return self._remove_namespace_from_key(key, self.monitoring_prefix, suffix)

    def _monitoring_keys_with_namespace(self, suffix, pattern='*'):
        """
        ('hits', '*') -> [py_auto_cache:namespace:'monitoring':'key1':'hits',
                          py_auto_cache:namespace:'monitoring':'key1':'hits',,
                          py_auto_cache:namespace:'monitoring':'key1':'hits',,
                          ...]

        :param pattern: pattern string like '*'
        :return: a list of matched keys with monitoring namespace like
                 [py_auto_cache:namespace:'monitoring':'key1':'hits',
                  py_auto_cache:namespace:'monitoring':'key1':'hits',,
                  py_auto_cache:namespace:'monitoring':'key1':'hits',,
                  ...]
        """
        return self._keys_with_namespace(pattern, self.monitoring_prefix, suffix)


def _remove_prefix(key, prefix):
    if key.startswith(prefix):
        key = key[len(prefix):]
    return key


def _remove_suffix(key, suffix):
    if key.endswith(suffix):
        key = key[:-len(suffix)]
    return key


def _convert_host(host):
    host_parts = host.split(':')
    if len(host_parts) == 1:
        return {'host': host_parts[0], 'port': 6379}
    elif len(host_parts) == 2:
        return {'host': host_parts[0], 'port': int(host_parts[1])}
    else:
        raise HostError('{} is not a normal host.'.format(host))
