#!/usr/bin/env python3
"""Regression tests for upgrading legacy cached media metadata."""

import unittest

from instagram_rss import berig_cache_post_medier, cache_post_har_mangelfulde_medier


class CacheUpgradeTests(unittest.TestCase):
    def test_detects_legacy_cache_post_without_media_fields(self):
        legacy_post = {
            "profil": "yuugen.archive",
            "url": "https://www.instagram.com/p/DWHShBEgaVM/",
            "billede": "https://example.com/cover.jpg",
        }

        self.assertTrue(cache_post_har_mangelfulde_medier(legacy_post))

    def test_upgrades_legacy_post_to_slideshow(self):
        cached_post = {
            "profil": "yuugen.archive",
            "url": "https://www.instagram.com/p/DWHShBEgaVM/",
            "billede": "https://example.com/cover.jpg",
        }
        medie_data = {
            "billede": "https://example.com/cover.jpg",
            "video": None,
            "medie_type": "slideshow",
            "ressourcer": [
                {"type": "billede", "thumbnail": "https://example.com/1.jpg", "video": None},
                {"type": "billede", "thumbnail": "https://example.com/2.jpg", "video": None},
            ],
        }

        changed = berig_cache_post_medier(cached_post, medie_data)

        self.assertTrue(changed)
        self.assertEqual(cached_post["medie_type"], "slideshow")
        self.assertEqual(len(cached_post["ressourcer"]), 2)
        self.assertFalse(cache_post_har_mangelfulde_medier(cached_post))


if __name__ == "__main__":
    unittest.main()
