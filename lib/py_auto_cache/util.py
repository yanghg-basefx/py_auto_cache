# -*- coding: utf-8 -*-
"""
Created by yanghg at 20-6-17 下午9:31
"""
from .error import ClientError

try:
    StringTypes = (str, unicode)


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
except NameError:
    StringTypes = (str, bytes)


    def transcode(s1):
        if isinstance(s1, bytes):
            return s1.decode('utf-8')
        elif isinstance(s1, str):
            return s1
        else:
            return str(s1)


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
