"""Exercise production cache headers with nginx: make test-nginx-cache."""

import http.client
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import uuid


def docker(*args):
    return subprocess.check_output(
        ["rtk", "proxy", "docker", *args], text=True, timeout=120
    ).strip()


class NginxCacheTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures = tempfile.TemporaryDirectory(prefix="cowallet-nginx-cache-")
        cls.addClassCleanup(fixtures.cleanup)
        cls.root = Path(fixtures.name)
        (cls.root / "assets").mkdir()
        (cls.root / "assets/app-abc123.js").write_text("console.log('fixture');")
        (cls.root / "assets/app-abc123.css").write_text("body { color: black; }")
        cls.html = cls.root / "index.html"
        cls.html.write_text("<!doctype html><title>release-a</title>")
        config = Path(__file__).resolve().parents[1] / "nginx.conf"
        name = "cowallet-nginx-cache-" + uuid.uuid4().hex[:12]
        docker(
            "run", "--detach", "--rm", "--name", name,
            "--add-host", "backend:127.0.0.1",
            "--publish", "127.0.0.1::80",
            "--volume", f"{config}:/etc/nginx/conf.d/default.conf:ro",
            "nginx:1.27-alpine",
        )
        cls.addClassCleanup(docker, "rm", "--force", name)
        cls.container = name
        docker("cp", f"{cls.root}/.", f"{name}:/usr/share/nginx/html")
        cls.port = int(docker("port", name, "80/tcp").rsplit(":", 1)[1])
        deadline = time.monotonic() + 10
        while True:
            try:
                cls.request("/")
                break
            except (OSError, http.client.HTTPException):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.1)

    def setUp(self):
        self.html.write_text("<!doctype html><title>release-a</title>")
        os.utime(self.html, (1700000000, 1700000000))
        docker("cp", str(self.html), f"{self.container}:/usr/share/nginx/html/index.html")

    @classmethod
    def request(cls, path, method="GET", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            body = response.read()
            return response.status, response.headers, body
        finally:
            connection.close()

    def test_config_is_valid(self):
        docker("exec", self.container, "nginx", "-t")

    def test_html_revalidates_for_all_entry_routes(self):
        for path in ("/", "/index.html", "/transactions", "/accounts/example", "/?v=1"):
            for method in ("GET", "HEAD"):
                with self.subTest(path=path, method=method):
                    status, headers, body = self.request(path, method)
                    self.assertEqual(status, 200)
                    self.assertEqual(headers.get_all("Cache-Control"), ["no-cache"])
                    self.assertIsNone(headers.get("Expires"))
                    self.assertIn("text/html", headers["Content-Type"])
                    self.assertEqual(body, b"" if method == "HEAD" else self.html.read_bytes())

    def test_unchanged_html_revalidates_with_both_validators(self):
        for path in ("/", "/index.html", "/transactions"):
            status, headers, _ = self.request(path)
            self.assertEqual(status, 200)
            for validator, value in (
                ("If-None-Match", headers["ETag"]),
                ("If-Modified-Since", headers["Last-Modified"]),
            ):
                with self.subTest(path=path, validator=validator):
                    status, headers, body = self.request(path, headers={validator: value})
                    self.assertEqual(status, 304)
                    self.assertEqual(headers.get_all("Cache-Control"), ["no-cache"])
                    self.assertEqual(body, b"")

    def test_changed_html_is_returned_for_old_validators(self):
        _, old, _ = self.request("/")
        self.html.write_text("<!doctype html><title>release-b</title>")
        os.utime(self.html, (1700000002, 1700000002))
        docker("cp", str(self.html), f"{self.container}:/usr/share/nginx/html/index.html")
        for validator, value in (
            ("If-None-Match", old["ETag"]),
            ("If-Modified-Since", old["Last-Modified"]),
        ):
            with self.subTest(validator=validator):
                status, headers, body = self.request("/", headers={validator: value})
                self.assertEqual(status, 200)
                self.assertEqual(headers.get_all("Cache-Control"), ["no-cache"])
                self.assertNotEqual(headers["ETag"], old["ETag"])
                self.assertEqual(body, self.html.read_bytes())

    def test_hashed_assets_remain_immutable(self):
        for path in ("/assets/app-abc123.js", "/assets/app-abc123.css"):
            with self.subTest(path=path):
                status, headers, body = self.request(path)
                self.assertEqual(status, 200)
                directives = ",".join(headers.get_all("Cache-Control"))
                self.assertIn("max-age=31536000", directives)
                self.assertIn("immutable", directives)
                self.assertIn("public", directives)
                self.assertNotIn("no-cache", directives)
                self.assertEqual(body, (self.root / path.lstrip("/")).read_bytes())

    def test_missing_assets_do_not_return_html_entry_point(self):
        status, _, body = self.request("/assets/missing.js")
        self.assertEqual(status, 404)
        self.assertNotEqual(body, self.html.read_bytes())


if __name__ == "__main__":
    unittest.main()
