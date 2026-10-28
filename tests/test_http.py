import io
import unittest
import urllib.error
from unittest.mock import patch

from biomed.io import request_json


class HttpTests(unittest.TestCase):
    def test_get_decodes_public_json(self):
        with patch("urllib.request.urlopen", return_value=io.StringIO('{"ok":true}')) as transport:
            data = request_json("https://example.org/annotations")
        self.assertEqual(data, {"ok": True})
        self.assertEqual(transport.call_args.args[0].get_method(), "GET")

    def test_transient_failure_is_retried(self):
        error = urllib.error.HTTPError("https://example.org", 503, "unavailable", {}, None)
        with patch("urllib.request.urlopen", side_effect=[error, io.StringIO('{"recovered":true}')]), patch("time.sleep"):
            self.assertEqual(request_json("https://example.org", retries=1), {"recovered": True})

    def test_http_failure_does_not_expose_response_body(self):
        error = urllib.error.HTTPError("https://example.org", 401, "secret-response", {}, io.BytesIO(b"private body"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401 from example.org") as raised:
                request_json("https://example.org")
        self.assertNotIn("private", str(raised.exception))
