#!/usr/bin/env python3
"""Regression tests for RSS title/body formatting."""

import unittest

from instagram_rss import byg_html_indhold, byg_post_titel


class HtmlOrderTests(unittest.TestCase):
    def test_title_does_not_repeat_profile_name(self):
        titel = byg_post_titel({
            "profil": "demo",
            "tekst": "En ret spændende billedtekst",
        })

        self.assertEqual(titel, "En ret spændende billedtekst")

    def test_single_image_is_rendered_before_caption(self):
        html_indhold = byg_html_indhold({
            "profil": "demo",
            "tekst": "Billedtekst her",
            "url": "https://example.com/post",
            "medie_type": "billede",
            "billede": "https://example.com/image.jpg",
            "video": None,
            "ressourcer": [],
        })

        self.assertLess(html_indhold.index("<img"), html_indhold.index("Billedtekst her"))
        self.assertLess(html_indhold.index("@demo"), html_indhold.index("Billedtekst her"))

    def test_slideshow_preview_is_rendered_before_caption(self):
        html_indhold = byg_html_indhold({
            "profil": "demo",
            "tekst": "Slideshow tekst",
            "url": "https://example.com/post",
            "medie_type": "slideshow",
            "billede": "https://example.com/cover.jpg",
            "video": None,
            "ressourcer": [
                {"thumbnail": "https://example.com/slide1.jpg", "video": None, "type": "billede"},
                {"thumbnail": "https://example.com/slide2.jpg", "video": None, "type": "billede"},
            ],
        })

        self.assertLess(html_indhold.index("<img"), html_indhold.index("Slideshow tekst"))
        self.assertLess(html_indhold.index("@demo"), html_indhold.index("Slideshow tekst"))

    def test_video_thumbnail_is_rendered_before_caption(self):
        html_indhold = byg_html_indhold({
            "profil": "demo",
            "tekst": "Video tekst",
            "url": "https://example.com/post",
            "medie_type": "video",
            "billede": "https://example.com/thumb.jpg",
            "video": "https://example.com/video.mp4",
            "ressourcer": [],
        })

        self.assertLess(html_indhold.index("<img"), html_indhold.index("Video tekst"))
        self.assertLess(html_indhold.index("@demo"), html_indhold.index("Video tekst"))

    def test_text_only_post_includes_profile_label_in_body(self):
        html_indhold = byg_html_indhold({
            "profil": "demo",
            "tekst": "Kun tekst",
            "url": "https://example.com/post",
            "medie_type": "billede",
            "billede": None,
            "video": None,
            "ressourcer": [],
        })

        self.assertIn("@demo", html_indhold)
        self.assertLess(html_indhold.index("@demo"), html_indhold.index("Kun tekst"))


if __name__ == "__main__":
    unittest.main()
