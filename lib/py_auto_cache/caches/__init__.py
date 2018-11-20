# -*- coding: utf-8 -*-
"""
Cache Clients Proxy
"""
try:
    from .redis_cache import RedisCache
except ImportError:
    RedisCache = None
try:
    from .dict_cache import DictCache
except ImportError:
    DictCache = None
try:
    from .dispatcher import Dispatcher
except ImportError:
    Dispatcher = None
