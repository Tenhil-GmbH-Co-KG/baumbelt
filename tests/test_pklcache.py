import pickle
from pathlib import Path
from unittest import TestCase

from src.baumbelt.cache import pklcache


class PklCacheTestCase(TestCase):
    def tearDown(self):
        Path("work.pkl").unlink(missing_ok=True)

    def test_pklcache(self):
        @pklcache
        def work(foo: int, bar: int):
            return foo + bar

        dest = Path("work.pkl")
        self.assertFalse(dest.exists())

        r = work(2, 3)
        self.assertEqual(r, 5)
        self.assertTrue(dest.exists())
        with open(dest, "rb") as f:
            unpickled = pickle.load(f)

        self.assertEqual(unpickled, r)
        dest.unlink()

    def test_pklcache_custom_destination(self):
        @pklcache(destination="tmp/work")
        def work(foo: int, bar: int):
            return foo + bar

        dest = Path("tmp/work.pkl")
        self.assertFalse(dest.exists())

        _ = work(2, 3)
        self.assertTrue(dest.exists())
        self.assertFalse(Path("work.pkl").exists())
        dest.unlink()

    def test_pklcache_force_refresh(self):
        @pklcache
        def work(foo: int, bar: int):
            return foo + bar

        dest = Path("work.pkl")
        _ = work(2, 3)
        r = work(200, 300)
        self.assertEqual(r, 5, "Known limitation: differing arguments dont alter the cached file")

        @pklcache(force_refresh=True)
        def work(foo: int, bar: int):
            return foo + bar

        r = work(200, 300)
        self.assertEqual(
            r,
            500,
            "With force_refresh, cached value should be equal to latest invocation",
        )
        r = work(2, 3)
        self.assertEqual(
            r,
            5,
            "Since pklcache is configured to force_refresh, altered arguments alter the cache",
        )
        dest.unlink()
