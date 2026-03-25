#!/usr/bin/env python3
"""Regression tests for generated RSS item titles."""

import unittest

from instagram_rss import byg_post_titel


class FeedTitleTests(unittest.TestCase):
    def test_title_does_not_repeat_profile_name(self):
        titel = byg_post_titel({
            "profil": "97kobo.lab",
            "tekst": "BYOM [Bring Your Own Machine] an open stage at 97KoboLab.",
        })

        self.assertEqual(titel, "BYOM [Bring Your Own Machine] an open stage at 97KoboLab.")

    def test_empty_caption_falls_back_to_profile(self):
        titel = byg_post_titel({
            "profil": "97kobo.lab",
            "tekst": "(ingen tekst)",
        })

        self.assertEqual(titel, "Post fra @97kobo.lab")


if __name__ == "__main__":
    unittest.main()
