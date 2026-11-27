import unittest

from src.base62 import decode
from src.hash_table import LinearProbingHashTable
from src.shortener import Shortener


class ShortenerTest(unittest.TestCase):
    def setUp(self):
        self.shortener = Shortener()

    def test_shorten_and_expand_valid_url(self):
        url = "https://example.com/path?query=value#section"

        code = self.shortener.shorten(url)

        self.assertIsInstance(code, str)
        self.assertEqual(self.shortener.expand(code), url)

    def test_same_url_returns_same_code(self):
        url = "https://example.com/path"

        first_code = self.shortener.shorten(url)
        second_code = self.shortener.shorten(url)

        self.assertEqual(second_code, first_code)

        new_code = self.shortener.shorten(
            "https://example.com/another"
        )

        self.assertEqual(decode(first_code), 1)
        self.assertEqual(decode(new_code), 2)

    def test_only_outer_whitespace_is_ignored(self):
        code = self.shortener.shorten("  https://a.com  ")

        self.assertEqual(self.shortener.shorten("https://a.com"), code)
        self.assertEqual(self.shortener.expand(code), "https://a.com")

    def test_distinct_url_components_receive_distinct_codes(self):
        urls = (
            "https://example.com/one",
            "https://example.com/two",
            "https://example.com/one?query=value",
            "https://example.com/one#section",
            "http://example.com/one",
        )

        codes = [self.shortener.shorten(url) for url in urls]

        for index, code in enumerate(codes):
            self.assertNotIn(code, codes[:index])
        for code, url in zip(codes, urls):
            self.assertEqual(self.shortener.expand(code), url)

    def test_scheme_validation_is_case_insensitive_but_identity_is_not_normalized(self):
        upper = "HTTPS://a.com"
        lower = "https://a.com"

        upper_code = self.shortener.shorten(upper)
        lower_code = self.shortener.shorten(lower)

        self.assertNotEqual(upper_code, lower_code)
        self.assertEqual(self.shortener.expand(upper_code), upper)
        self.assertEqual(self.shortener.expand(lower_code), lower)

    def test_invalid_urls_raise_value_error(self):
        invalid_urls = (
            "",
            "   ",
            "ftp://example.com/file",
            "https:///path-without-host",
            "https://example.com/path with space",
            "https://example.com/path\twith-tab",
            "https://example.com/path\x00",
        )

        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.shortener.shorten(url)

    def test_non_string_url_raises_type_error(self):
        with self.assertRaises(TypeError):
            self.shortener.shorten(None)

    def test_invalid_url_does_not_consume_id_or_store_entry(self):
        with self.assertRaises(ValueError):
            self.shortener.shorten("not a URL")

        self.assertIsNone(self.shortener.expand("1"))

        code = self.shortener.shorten("https://example.com")

        self.assertEqual(decode(code), 1)
        self.assertEqual(self.shortener.expand(code), "https://example.com")

    def test_url_length_limit_is_applied_after_trimming(self):
        prefix = "https://a.com/"
        url_at_limit = prefix + "x" * (2048 - len(prefix))
        code = self.shortener.shorten(f"  {url_at_limit}  ")
        self.assertEqual(self.shortener.expand(code), url_at_limit)

        url_over_limit = prefix + "x" * (2049 - len(prefix))
        with self.assertRaises(ValueError):
            self.shortener.shorten(url_over_limit)

    def test_expand_unknown_code_returns_none(self):
        self.assertIsNone(self.shortener.expand("unknown"))


class LinearProbingShortenerTest(ShortenerTest):
    def setUp(self):
        self.shortener = Shortener(table_type=LinearProbingHashTable)


if __name__ == "__main__":
    unittest.main()
