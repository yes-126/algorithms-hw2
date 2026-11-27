import http.client
import threading
import unittest
from urllib.parse import urlencode

from src.hash_table import HashTable
from src.server import make_server


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.server = make_server(host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(self.host, self.port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        status = response.status
        response_headers = response.headers
        response_body = response.read().decode("utf-8")
        connection.close()
        return status, response_headers, response_body

    def test_home_page_has_url_form_and_table_link(self):
        status, headers, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn('action="/shorten"', body)
        self.assertIn('name="url"', body)
        self.assertIn('href="/table"', body)

    def test_shortening_redirects_to_original_url(self):
        url = "https://example.com/path?query=value#section"
        status, _, body = self.request(
            "POST",
            "/shorten",
            body=urlencode({"url": url}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        self.assertEqual(status, 200)
        self.assertIn("http://127.0.0.1:", body)
        self.assertIn('href="http://127.0.0.1:', body)

        code = body.split("/l/", 1)[1].split('"', 1)[0]
        redirect_status, redirect_headers, _ = self.request("GET", f"/l/{code}")
        self.assertEqual(redirect_status, 302)
        self.assertEqual(redirect_headers["Location"], url)

    def test_form_uses_forwarded_origin_when_present(self):
        status, _, body = self.request(
            "POST",
            "/shorten",
            body=urlencode({"url": "https://example.com/"}),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Forwarded-Host": "short.example:8443",
                "X-Forwarded-Proto": "https",
            },
        )

        self.assertEqual(status, 200)
        self.assertIn("https://short.example:8443/l/", body)

    def test_invalid_url_returns_bad_request_error(self):
        status, _, body = self.request(
            "POST",
            "/shorten",
            body=urlencode({"url": "ftp://example.com/file"}),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        self.assertEqual(status, 400)
        self.assertIn("Error", body)

    def test_unknown_code_returns_not_found_error(self):
        status, _, body = self.request("GET", "/l/not-a-code")

        self.assertEqual(status, 404)
        self.assertIn("Error", body)

    def test_table_shows_chained_url_nodes_and_expandable_hash_trace(self):
        first_url = "https://example.com/?q=<tag>&next=/home"
        target_bucket = HashTable._index_for(first_url, 8)
        second_url = None
        for number in range(1000):
            candidate = f"https://example.org/collision/{number}"
            if HashTable._index_for(candidate, 8) == target_bucket:
                second_url = candidate
                break
        self.assertIsNotNone(second_url)

        for url in (first_url, second_url):
            self.request(
                "POST",
                "/shorten",
                body=urlencode({"url": url}),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("버킷 수", body)
        self.assertIn("적재율", body)
        self.assertIn("&lt;tag&gt;", body)
        self.assertNotIn("<tag>", body)
        self.assertIn("→", body)
        self.assertIn("<details>", body)
        self.assertIn("ord(", body)
        self.assertIn('href="http://127.0.0.1:', body)
        self.assertIn("선형 탐지", body)
        self.assertIn("최초 해시 인덱스", body)
        self.assertIn("들여다본 칸", body)
        self.assertIn("최종 저장 인덱스", body)


if __name__ == "__main__":
    unittest.main()
