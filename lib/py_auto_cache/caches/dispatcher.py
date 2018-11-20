# -*- coding: utf-8 -*-
"""
Created by yanghg at 18-5-17 上午8:45
"""
from ..cache import Cache, ClientError, wrap_client_exception


class DispatcherClientError(ClientError):
    """
    Base class for all errors come from cache manager
    """


dispatcher_error_wrapper = wrap_client_exception((TypeError, ValueError), DispatcherClientError)


class Dispatcher(Cache):
    """
    Implement cache manager to control primary cache and alternate caches

    Most of operations will execute to primary cache, only ``delete`` will affect all the caches
    """

    def __init__(self, dispatched_caches):
        """
        Init cache manager by a list of cache proxies

        :param list[Cache] dispatched_caches: a list of caches, the first item will be primary,
                                        so you should add at least one item.
                                        You can change this list later even though
                                        the dispatcher has been constructed
        """
        super(Dispatcher, self).__init__()

        if len(dispatched_caches) < 1:
            raise ValueError('cache_proxies needs at least one item')

        invalid_indexes = []
        for index, dispatched_cache in enumerate(dispatched_caches):
            if not isinstance(dispatched_cache, Cache):
                invalid_indexes.append(index)
        if len(invalid_indexes) > 0:
            raise TypeError(
                'items with the index of {} are not inherited from CacheProxy'.format(tuple(invalid_indexes)))

        self._dispatched_caches = dispatched_caches

    def get(self, key):
        return self._dispatched_caches[0].get(key)

    def set(self, key, value, expire_seconds=None, only_if_new=False, only_if_old=False):
        return self._dispatched_caches[0].set(key, value, expire_seconds, only_if_new, only_if_old)

    def delete(self, keys):
        return [dispatched_cache.delete(keys) for dispatched_cache in self._dispatched_caches]

    def get_keys(self, pattern='*'):
        return self._dispatched_caches[0].get_keys(pattern)

    def increase(self, key, amount=1):
        return self._dispatched_caches[0].increase(key, amount)

    def multi_get(self, keys):
        return self._dispatched_caches[0].multi_get(keys)

    def clear(self, pattern='*'):
        deleted_count = 0
        for dispatched_cache in self._dispatched_caches:
            deleted_count += dispatched_cache.clear(pattern)
        return deleted_count
