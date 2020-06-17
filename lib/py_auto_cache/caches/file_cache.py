# -*- coding: utf-8 -*-
"""
Created by yanghg at 18-11-19 下午5:05
"""
import json
import os
import hashlib
import time
import fnmatch
import tempfile
from ..cache import Cache
from ..error import ClientError
from ..util import wrap_client_exception, transcode


class FileClientError(ClientError):
    """
    Base class for all errors come from file client
    """


class ParameterError(FileClientError):
    """
    Be raised if the parameter is invalid
    """


file_error_wrapper = wrap_client_exception((IndexError, KeyError, ValueError, IOError), FileClientError)


def get_md5(key):
    md5 = hashlib.md5()
    md5.update(key)
    return md5.hexdigest()


class FileCache(Cache):
    """
    Implement a local cache server by python file
    """

    cache_root = os.path.join(tempfile.gettempdir(), 'cache')

    def __init__(self, cache_root=None):
        super(FileCache, self).__init__()
        self._cache_root = self.cache_root if cache_root is None else cache_root

    def _get_fp(self, key):
        return os.path.join(self._cache_root, get_md5(key))

    def _read(self, fp):
        if not os.path.isfile(fp):
            return {}
        with open(fp) as f:
            return json.load(f, 'ascii')

    def _write(self, key, value, fp):
        if os.path.isfile(fp):
            jd = self._read(fp)
        else:
            if not os.path.isdir(self._cache_root):
                os.makedirs(self._cache_root)
            jd = {}
        if value is None:
            if key in jd:
                del jd[key]
            else:
                return False
        else:
            jd[key] = value
        with open(fp, 'w') as f:
            json.dump(jd, f, encoding='ascii')
        return True

    @file_error_wrapper
    def get(self, key):
        key = transcode(key)
        fp = self._get_fp(key)
        jd = self._read(fp)
        value_tuple = jd.get(key, None)
        if value_tuple is None:
            return None
        if value_tuple[2] is not None and time.time() - value_tuple[1] > value_tuple[2]:
            self._write(key, None, fp)
            return None
        return transcode(value_tuple[0])

    @file_error_wrapper
    def set(self, key, value, expire_seconds=None, only_if_new=False, only_if_old=False):
        key = transcode(key)
        fp = self._get_fp(key)
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
            self._write(key, (value, time.time(), expire_seconds), fp)
            return True
        return False

    @file_error_wrapper
    def delete(self, keys):
        count = 0
        for key in keys:
            key = transcode(key)
            fp = self._get_fp(key)
            if self._write(key, None, fp):
                count += 1
        return count

    @file_error_wrapper
    def get_keys(self, pattern='*'):
        pattern = transcode(pattern)
        keys = []
        if not os.path.isdir(self._cache_root):
            return keys
        for fn in os.listdir(self._cache_root):
            fp = os.path.join(self._cache_root, fn)
            with open(fp) as f:
                for key in json.load(f):
                    if fnmatch.fnmatch(key, pattern):
                        keys.append(key)

        return keys

    @file_error_wrapper
    def increase(self, key, amount=1):
        key = transcode(key)
        return super(FileCache, self).increase(key, amount)

    @file_error_wrapper
    def multi_get(self, keys):
        keys = [transcode(key) for key in keys]
        return super(FileCache, self).multi_get(keys)

    @file_error_wrapper
    def clear(self, pattern='*'):
        pattern = transcode(pattern)
        return super(FileCache, self).clear(pattern)
