AutoRedis
==================================================

Overview
--------------------------------------------------

This is a package that implements an easy-to-use framework for using redis based caches.

It provides some classes and function that make it very easy to decorate your functions in
boilerplate code that handles caching of function calls in a redis cache within a namespace.


Dependence
--------------------------------------------------

This module is dependent on:

> [redis](https://redis.io/download)

> inspect

> pickle

Modules
--------------------------------------------------

#### cache.py

Implements Cache, a class that provides a namespaced interface to a redis cache.


#### auto_cache.py

Implements AutoCache, a subclass of Cache that adds the ability to easily use a decorator on any function,
automatically adding cache support to the function.

Client code's only interaction with this module should be through the following functions:
    auto_cache_decorator()
    get_auto_cache()

Example
--------------------------------------------------

```python
from py_auto_cache import auto_cache_decorator, get_auto_cache

@auto_cache_decorator(namespace='test', default_expiry=3600)
def run(*args):
    print('executing function')
    return args

print(run(1))
```

> executing function

> (1,)

```python
print(run(2, 3))
```

> executing function

> (2, 3)

```python
print(run(4, 5, 6))
```

> executing function

> (4, 5, 6)

```python
print(run(4, 5, 6))
```

> (4, 5, 6)

```python
print(run(4, 5, 6, update_auto_cache=True))
```

> executing function

>(4, 5, 6)

```python
print(run(2, 3))
```

> (2, 3)

```python
cache = get_auto_cache(namespace='test', expire_time=3600)
cache.clear()   # clear all entries in the cache in our namespace

print(run(2, 3))
```

> executing function

> (2, 3)

```python
print(run(1))
```

> executing function

> (1,)

Advanced
-------------------------------------------------

You could specify the cache key if you don't want to use pickle to dump all
of your params, especially you use a django/peewee/sqlalchemy ORM object 
as a key.

```python
from py_auto_cache.auto_cache import AutoCache

orm_cache = AutoCache(namespace='test')

@orm_cache.decorator(key=lambda obj: obj.id)
def get_first_children(obj):
    return obj.children.order_by(Children.id.desc()).first()
```

You could also get original function, bind key and full cache prefix 
if you want.

```python
print(get_first_children.__source_func__)
print(get_first_children.__source_func__.__bind_key__)
print(get_first_children.__source_func__.__full_cache_prefix__)
``` 

Author
-------------------------------------------------

This module is wrote by Yang Hanguang, Ramin Kamal


Thank
--------------------------------------------------

Thanks for Nathan to give me the first version of redis cache. That's a good start.

Please click [here](https://github.com/vivekn/redis-simple-cache) to see the redis-simple-cache wrote by vivekn.
