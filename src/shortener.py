import unicodedata
from urllib.parse import urlsplit

from src.base62 import encode
from src.hash_table import HashTable


class Shortener:
    def __init__(self):
        self._url_to_code = HashTable()
        self._code_to_url = HashTable()
        self._next_id = 1

    def shorten(self, url):
        normalized_url = self._validate_url(url)
        existing_code = self._url_to_code.get(normalized_url)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_id)
        self._url_to_code.put(normalized_url, code)
        self._code_to_url.put(code, normalized_url)
        self._next_id += 1
        return code

    def expand(self, code):
        return self._code_to_url.get(code)

    @staticmethod
    def _validate_url(url):
        if not isinstance(url, str):
            raise TypeError("url must be a string")

        normalized_url = url.strip()
        if not normalized_url:
            raise ValueError("url must not be empty")
        if len(normalized_url) > 2048:
            raise ValueError("url must not exceed 2048 characters")
        if any(
            character.isspace() or unicodedata.category(character) == "Cc"
            for character in normalized_url
        ):
            raise ValueError("url must not contain whitespace or control characters")

        try:
            parsed_url = urlsplit(normalized_url)
            hostname = parsed_url.hostname
            parsed_url.port
        except ValueError as error:
            raise ValueError("url is invalid") from error

        if parsed_url.scheme.lower() not in ("http", "https") or not hostname:
            raise ValueError("url must have an http or https scheme and a host")

        return normalized_url
