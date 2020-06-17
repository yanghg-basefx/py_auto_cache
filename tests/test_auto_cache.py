# -*- coding: utf-8 -*-

import os
import time
from unittest import TestCase

from py_auto_cache import *
from py_auto_cache.caches import RedisCache

run_times = 0
auto_cache = get_auto_cache('unittest', 3600, RedisCache(os.environ.get('REDIS_HOST', 'localhost')))


@auto_cache.decorator
def run(*args):
    global run_times
    run_times += 1
    return args


@auto_cache.decorator
def specific_args(func):
    return func


class TestAutoCache(TestCase):
    def test_cache(self):
        global run_times
        run_times = 0

        auto_cache.clear()
        self.assertEqual(len(auto_cache.get_keys()), 0)

        self.assertEqual(run(1), (1,))
        self.assertEqual(run(1), (1,))
        self.assertEqual(run_times, 1)

        self.assertEqual(run(2, 3), (2, 3))
        self.assertEqual(run(2, 3), (2, 3))
        self.assertEqual(run_times, 2)

        self.assertEqual(run(4, 5, 6), (4, 5, 6))
        self.assertEqual(run(4, 5, 6), (4, 5, 6))
        self.assertEqual(run(4, 5, 6), (4, 5, 6))
        self.assertEqual(run_times, 3)

        self.assertEqual(len(auto_cache.get_keys()), 3)
        for key in auto_cache._keys_with_namespace():
            self.assertTrue(key.startswith('py_auto_cache:unittest'))

        auto_cache.clear()
        self.assertEqual(len(auto_cache.get_keys()), 0)

        run_times = 0

    def test_specific_args(self):
        self.assertTrue(specific_args(func='func') == 'func')


@auto_cache.decorator
def sometimes_cache(to_cache_or_not_to_cache):
    time_to_return = time.time()
    time.sleep(0.01)    # to make sure we don't get the same result twice

    if to_cache_or_not_to_cache:
        return time_to_return
    raise DoNotCacheException(time_to_return)


class TestDoNotAutoCache(TestCase):
    def test_cache(self):
        auto_cache.clear()
        self.assertNotEqual(sometimes_cache(False), sometimes_cache(False))

        self.assertEqual(sometimes_cache(True), sometimes_cache(True))


# global var used in already_called function
firsttime = True


@auto_cache.decorator
def already_called():
    # if cached correctly, this will always return False
    global firsttime
    if firsttime:
        firsttime = False
        return False
    return True


# global var used to count number of calls to return_none
return_none_calls = 0


@auto_cache.decorator
def return_none():
    global return_none_calls
    return_none_calls += 1
    return None


class TestEdgeCases(TestCase):
    def test_false_return(self):
        self.assertFalse(already_called())
        self.assertFalse(already_called())

    def test_none_return(self):
        global return_none_calls
        self.assertIsNone(return_none())
        self.assertIsNone(return_none())
        self.assertIsNone(return_none())
        self.assertEqual(return_none_calls, 1)
