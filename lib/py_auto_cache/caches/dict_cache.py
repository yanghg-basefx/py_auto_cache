# -*- coding: utf-8 -*-
"""
Created by yanghg at 18-5-7 下午5:41
"""
import time
import fnmatch
from ..cache import Cache, ClientError, wrap_client_exception


class DictClientError(ClientError):
    """
    Base class for all errors come from dict client
    """


class ParameterError(DictClientError):
    """
    Be raised if the parameter is invalid
    """


dict_error_wrapper = wrap_client_exception((IndexError, KeyError, ValueError), DictClientError)


def transcode(s1):
    """
    Transcode the given string/unicode/other-object to utf-8 str

    :param s1:
    :return:
    """
    if isinstance(s1, str):
        return s1
    elif isinstance(s1, unicode):
        return s1.encode('utf-8')
    else:
        return str(s1)


class DictCache(Cache):
    """
    Implement a local cache server by python dict
    """

    def __init__(self):
        super(DictCache, self).__init__()
        self._dict = {}

    @dict_error_wrapper
    def get(self, key):
        key = transcode(key)
        value_tuple = self._dict.get(key)
        if value_tuple is None:
            return None
        if value_tuple[2] is not None and time.time() - value_tuple[1] > value_tuple[2]:
            del self._dict[key]
            return None
        return value_tuple[0]

    @dict_error_wrapper
    def set(self, key, value, expire_seconds=None, only_if_new=False, only_if_old=False):
        key = transcode(key)
        value = transcode(value)
        if only_if_new and only_if_old:
            raise ParameterError('You can only give one of only_if_new or only_if_old')

        _set_flag = True
        _key_in_cache = self.get(key) is not None
        if only_if_new and _key_in_cache:
            _set_flag = False
        if only_if_old and not _key_in_cache:
            _set_flag = False

        if _set_flag:
            self._dict[key] = (value, time.time(), expire_seconds)
            return True
        return False

    @dict_error_wrapper
    def delete(self, keys):
        count = 0
        for key in keys:
            key = transcode(key)
            if key in self._dict:
                del self._dict[key]
                count += 1
        return count

    @dict_error_wrapper
    def get_keys(self, pattern='*'):
        pattern = transcode(pattern)
        return [key for key in self._dict.keys() if fnmatch.fnmatch(key, pattern)]

    @dict_error_wrapper
    def increase(self, key, amount=1):
        key = transcode(key)
        return super(DictCache, self).increase(key, amount)

    @dict_error_wrapper
    def multi_get(self, keys):
        keys = [transcode(key) for key in keys]
        return super(DictCache, self).multi_get(keys)

    @dict_error_wrapper
    def clear(self, pattern='*'):
        pattern = transcode(pattern)
        return super(DictCache, self).clear(pattern)
