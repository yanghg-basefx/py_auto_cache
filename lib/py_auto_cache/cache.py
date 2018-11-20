# -*- coding: utf-8 -*-
import abc
import six
from .error import CacheError


class ClientError(CacheError):
    """
    Base class for all errors come from client
    """


def wrap_client_exception(src_exception_cls, dst_exception_cls=ClientError):
    """
    Use this wrapper to wrap original exception classes

    This wrapper will catch all exceptions of class, src_exception_cls,
    and re-raise them as new exceptions which are new subclasses of the class dst_exception_cls.
    This is useful so that client code can generally catch exceptions of type dst_exception_class
    to catch arbitrary exceptions that aren't explicitly defined in the cache interface.

    :param tuple|Exception src_exception_cls: The exceptions which you want to catch
    :param Exception dst_exception_cls: Base exception class which you want to inherit from
    :return: wrapper
    """
    exception_classes = {}

    def wrapper(func):
        def new_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except src_exception_cls as e:
                r_cls = e.__class__
                inherit_from = (r_cls, dst_exception_cls,)
                if inherit_from not in exception_classes:
                    # create a class named r_cls.name
                    # that multiply inherits from dst_exception_cls AND src_exception_cls.
                    exception_classes[inherit_from] = type(r_cls.__name__, inherit_from, {})
                raise exception_classes[inherit_from](e)

        return new_func

    return wrapper


engine_error_wrapper = wrap_client_exception(ValueError, ClientError)


@six.add_metaclass(abc.ABCMeta)
class Cache(object):
    """
    A generic interface for cache clients. Subclasses can be used to implement
    different cache types. eg memcached, redis, and even in RAM dicts.
    """

    @abc.abstractmethod
    def get(self, key):
        """
        Get value for the given key

        Returns None if there is no match.

        :param str|unicode key: Cache key
        :return: Cache value
        :rtype: str
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set(self, key, value, expire_seconds=None, only_if_new=False, only_if_old=False):
        """
        Set value for the given key

        Some options are provided, please implement them as well by yourself.

        :param str|unicode key: Cache key
        :param str|unicode value: Cache value
        :param float expire_seconds: Maybe you need to provide this param to tell cache server
                                   how long do you want this key to live.
        :param bool only_if_new: the set should only happen if the key does NOT exist in the cache
        :param bool only_if_old: the set should only happen if the key DOES exist in the cache
        :return: Return True if set successfully
        :rtype: bool
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, keys):
        """
        Delete the given keys

        :param list[str|unicode] keys: all the keys you need to delete
        :return: how many keys are deleted successfully
        :rtype: int
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_keys(self, pattern='*'):
        """
        Get all keys that match the given pattern

        Pattern can contain: * ? [abc]

        :param str|unicode pattern: contains * ? [abc]
        :return: a list of string contains all the matching keys
        :rtype: list[str]
        """
        raise NotImplementedError

    @engine_error_wrapper
    def increase(self, key, amount=1):
        """
        Increase value by amount

        Is equivalent to: cache[key] += amount

        :param str|unicode key: Cache key
        :param int amount: Increase step
        :return: value after increased
        :rtype: str
        """
        value = self.get(key)
        if value is None:
            increased_value = str(amount)
        elif isinstance(value, (str, unicode)) and value.isdigit():
            increased_value = str(int(value) + amount)
        else:
            raise ValueError('Value({}) of key({}) is not an integer'.format(repr(value), repr(key)))
        self.set(key, increased_value)

        return increased_value

    def multi_get(self, keys):
        """
        Get values using the given keys (keys cannot be patterns)

        :param list[str|unicode] keys: all the keys you need to get
        :return: a list of string contains all the values.
                 if one key doesn't found, the value at that index will be set to None
        :rtype: list[str]
        """
        return [self.get(key) for key in keys]

    def clear(self, pattern='*'):
        """
        Clear keys by the given pattern

        Pattern can contain: * ? [abc]

        :param str|unicode pattern: contains * ? [abc]
        :return: how many keys are deleted successful
        :rtype: int
        """
        return self.delete(self.get_keys(pattern))

    def memory_size(self, keys):
        """
        Returns the number of bytes being consumed in the cache by given keys.
        The returned value might be an approximation.

        :param list[str|unicode] keys: keys need to calculate memory size
        :return: the number of bytes by given keys
        :rtype: int
        """
        if keys:
            values = self.multi_get(keys)
        else:
            values = []

        return _calculate_size(keys) + _calculate_size(values)


def _calculate_size(something):
    return sum(len(item) for item in something if isinstance(item, basestring))
