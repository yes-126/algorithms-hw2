import argparse
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, unquote, urlsplit

from src.hash_table import LinearProbingHashTable
from src.shortener import Shortener


_MAX_FORM_BYTES = 16384


def _safe_authority(authority):
    if not authority or any(
        character.isspace() or ord(character) < 32 or character in "/\\?#@"
        for character in authority
    ):
        return None

    try:
        parsed = urlsplit("//" + authority)
        if not parsed.hostname or parsed.netloc != authority:
            return None
        parsed.port
    except ValueError:
        return None

    return authority


def _first_forwarded_value(value):
    if value is None:
        return None
    return value.split(",", 1)[0].strip()


def _hash_trace(key, capacity):
    value = 0
    steps = []
    for character in key:
        next_value = (value * 31 + ord(character)) % capacity
        steps.append(
            f"h = ({value} * 31 + ord({character!r})) % {capacity} = {next_value}"
        )
        value = next_value
    return steps, value


def _make_handler(shortener, linear_shortener):
    class ShortenerRequestHandler(BaseHTTPRequestHandler):
        server_version = "URLShortener/1.0"

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/":
                self._send_html(200, self._home_page())
                return
            if path == "/table":
                self._send_html(200, self._table_page())
                return
            if path.startswith("/l/"):
                code = unquote(path[len("/l/"):])
                url = shortener.expand(code)
                if url is None:
                    self._send_html(404, self._error_page())
                    return
                self.send_response(302)
                self.send_header("Location", url)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            self._send_html(404, self._error_page())

        def do_POST(self):
            if urlsplit(self.path).path != "/shorten":
                self._send_html(404, self._error_page())
                return

            form = self._read_form()
            if form is None:
                return
            url = None
            for name, value in form:
                if name == "url":
                    url = value
                    break
            if url is None:
                self._send_html(400, self._error_page())
                return

            try:
                code = shortener.shorten(url)
            except (TypeError, ValueError):
                self._send_html(400, self._error_page())
                return
            linear_code = linear_shortener.shorten(url)
            if linear_code != code:
                raise RuntimeError("hash table implementations issued different codes")

            short_url = f"{self._origin()}/l/{code}"
            escaped_url = html.escape(short_url, quote=True)
            page = (
                "<!doctype html><html lang=\"ko\"><meta charset=\"utf-8\">"
                "<title>단축 결과</title><body><h1>단축 결과</h1>"
                f'<p><a href="{escaped_url}">{escaped_url}</a></p>'
                '<p><a href="/">다른 URL 줄이기</a></p></body></html>'
            )
            self._send_html(200, page)

        def _read_form(self):
            content_type = self.headers.get("Content-Type", "")
            if content_type.split(";", 1)[0].strip().lower() != (
                "application/x-www-form-urlencoded"
            ):
                self._send_html(400, self._error_page())
                return None

            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_html(400, self._error_page())
                return None
            if content_length < 0:
                self._send_html(400, self._error_page())
                return None
            if content_length > _MAX_FORM_BYTES:
                self._send_html(413, self._error_page())
                return None

            body = self.rfile.read(content_length)
            try:
                encoded_form = body.decode("utf-8")
                return parse_qsl(
                    encoded_form,
                    keep_blank_values=True,
                    max_num_fields=100,
                    encoding="utf-8",
                    errors="strict",
                )
            except (UnicodeDecodeError, ValueError):
                self._send_html(400, self._error_page())
                return None

        def _origin(self):
            forwarded_host = _first_forwarded_value(
                self.headers.get("X-Forwarded-Host")
            )
            authority = _safe_authority(forwarded_host)
            if authority is None:
                authority = _safe_authority(self.headers.get("Host", ""))
            if authority is None:
                server_host, server_port = self.server.server_address[:2]
                if ":" in server_host and not server_host.startswith("["):
                    server_host = f"[{server_host}]"
                authority = f"{server_host}:{server_port}"

            forwarded_proto = _first_forwarded_value(
                self.headers.get("X-Forwarded-Proto")
            )
            scheme = forwarded_proto.lower() if forwarded_proto else "http"
            if scheme not in ("http", "https"):
                scheme = "http"
            return f"{scheme}://{authority}"

        def _home_page(self):
            return (
                "<!doctype html><html lang=\"ko\"><meta charset=\"utf-8\">"
                "<title>URL 단축기</title><body><h1>URL 단축기</h1>"
                '<form action="/shorten" method="post">'
                '<label for="url">줄일 URL</label> '
                '<input id="url" name="url" type="url" required>'
                '<button type="submit">줄이기</button></form>'
                '<p><a href="/table">해시 테이블 보기</a></p>'
                "</body></html>"
            )

        def _table_page(self):
            return (
                "<!doctype html><html lang=\"ko\"><meta charset=\"utf-8\">"
                "<title>현재 해시 테이블</title><body>"
                "<h1>현재 URL 해시 테이블</h1>"
                f"{self._chaining_table_html(shortener._url_to_code)}"
                f"{self._linear_table_html(linear_shortener._url_to_code)}"
                '<p><a href="/">URL 줄이기</a></p></body></html>'
            )

        def _render_node(self, key, code, table, probe_data=None):
            escaped_key = html.escape(key, quote=True)
            escaped_code = html.escape(code, quote=True)
            short_url = f"{self._origin()}/l/{code}"
            escaped_short_url = html.escape(short_url, quote=True)
            steps, initial_index = _hash_trace(key, table.capacity)
            trace = "".join(
                f"<li><code>{html.escape(step)}</code></li>" for step in steps
            )
            if not trace:
                trace = "<li><code>h = 0</code> (빈 키)</li>"

            details = (
                "<details><summary>호너 해시 계산 과정</summary>"
                f"<ol>{trace}</ol>"
                f"<p>최초 해시 인덱스: {initial_index}</p>"
            )
            if probe_data is None:
                details += f"<p>최종 저장 인덱스: {initial_index}</p>"
            else:
                probe_initial, inspected_indices, final_index = probe_data
                inspected = " → ".join(str(index) for index in inspected_indices)
                details += (
                    f"<p>최초 해시 인덱스: {probe_initial}</p>"
                    f"<p>충돌로 들여다본 칸: {inspected}</p>"
                    f"<p>최종 저장 인덱스: {final_index}</p>"
                    "<p>선형 탐지는 최초 인덱스에서 시작해 한 칸씩 이동하고, "
                    "빈 칸 또는 같은 키를 찾을 때까지 배열 끝에서 0번 칸으로 순환합니다.</p>"
                )
            details += "</details>"

            return (
                '<span class="node">'
                f"<strong>URL 키:</strong> <code>{escaped_key}</code><br>"
                f"<strong>짧은 코드:</strong> <code>{escaped_code}</code><br>"
                f'<strong>짧은 링크:</strong> <a href="{escaped_short_url}">'
                f"{escaped_short_url}</a>"
                f"{details}</span>"
            )

        def _chaining_table_html(self, table):
            rows = []
            for bucket_index, head in enumerate(table._buckets):
                nodes = []
                node = head
                while node is not None:
                    nodes.append(self._render_node(node.key, node.value, table))
                    node = node.next
                chain = " → ".join(nodes) if nodes else "—"
                rows.append(
                    f"<tr><th scope=\"row\">{bucket_index}</th><td>{chain}</td></tr>"
                )
            return (
                "<h2>개별 체이닝 해시 테이블</h2>"
                f"<p>버킷 수: {table.capacity} · 저장 항목 수: {len(table)}"
                f" · 적재율: {table.load_factor:.4f}</p>"
                '<table border="1"><thead><tr><th>버킷</th>'
                "<th>연결 리스트 노드</th></tr></thead><tbody>"
                f"{''.join(rows)}</tbody></table>"
            )

        def _linear_table_html(self, table):
            rows = []
            for index, key, code, deleted in table.iter_slots():
                if key is None:
                    cell = "삭제 표시자" if deleted else "—"
                else:
                    cell = self._render_node(
                        key, code, table, table.probe_trace(key)
                    )
                rows.append(
                    f"<tr><th scope=\"row\">{index}</th><td>{cell}</td></tr>"
                )
            return (
                "<h2>선형 탐지 해시 테이블</h2>"
                f"<p>칸 수: {table.capacity} · 저장 항목 수: {len(table)}"
                f" · 적재율: {table.load_factor:.4f}</p>"
                '<table border="1"><thead><tr><th>칸</th>'
                "<th>저장 노드와 탐색 근거</th></tr></thead><tbody>"
                f"{''.join(rows)}</tbody></table>"
            )

        @staticmethod
        def _error_page():
            return (
                "<!doctype html><html lang=\"ko\"><meta charset=\"utf-8\">"
                "<title>Error</title><body><p>Error</p>"
                '<p><a href="/">돌아가기</a></p></body></html>'
            )

        def _send_html(self, status, body):
            encoded_body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded_body)))
            self.end_headers()
            self.wfile.write(encoded_body)

    return ShortenerRequestHandler


def make_server(host="0.0.0.0", port=8000, shortener=None, linear_shortener=None):
    if shortener is None:
        shortener = Shortener()
    if linear_shortener is None:
        linear_shortener = Shortener(table_type=LinearProbingHashTable)
        for url, code in shortener._url_to_code.iter_entries():
            linear_shortener._url_to_code.put(url, code)
            linear_shortener._code_to_url.put(code, url)
        linear_shortener._next_id = shortener._next_id
    return HTTPServer(
        (host, port), _make_handler(shortener, linear_shortener)
    )


def main():
    parser = argparse.ArgumentParser(description="Run the URL shortener web server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()

    server = make_server(host=arguments.host, port=arguments.port)
    print(f"Serving on http://{arguments.host}:{arguments.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
