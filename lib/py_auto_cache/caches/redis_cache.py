# -*- coding: utf-8 -*-
from redis import StrictRedis, RedisError
from ..cache import Cache
from ..error import ClientError
from ..util import wrap_client_exception


class RedisClientError(ClientError):
    """
    Base class for all errors come from redis client
    """


redis_error_wrapper = wrap_client_exception(RedisError, RedisClientError)


class RedisCache(Cache):
    """
    Implement redis cache
    """

    def __init__(self, host='localhost', port=6379, timeout=None):
        super(RedisCache, self).__init__()

        self._redis = StrictRedis(host, port, socket_timeout=timeout, socket_connect_timeout=timeout)

    @redis_error_wrapper
    def get(self, key):
        return self._redis.get(key)

    @redis_error_wrapper
    def set(self, key, value, expire_seconds=None, only_if_new=False, only_if_old=False):
        expire_milliseconds = None
        if expire_seconds is not None:
            expire_milliseconds = int(expire_seconds * 1000)

        return self._redis.set(key, value, None, expire_milliseconds, only_if_new, only_if_old)

    @redis_error_wrapper
    def delete(self, keys):
        if len(keys) > 0:
            return self._redis.delete(*keys)
        return 0

    @redis_error_wrapper
    def get_keys(self, pattern='*'):
        return self._redis.keys(pattern)

    @redis_error_wrapper
    def increase(self, key, amount=1):
        return self._redis.incr(key, amount)

    @redis_error_wrapper
    def multi_get(self, keys):
        if len(keys) > 0:
            return self._redis.mget(keys)
        return []

    @redis_error_wrapper
    def clear(self, pattern='*'):
        return super(RedisCache, self).clear(pattern)
