"""Test the Tasks statistics proxy with fake upstream responses."""

import io
import json
import os
import socket
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from services.tasks import app as tasks


class StatisticsProxyTests(unittest.TestCase):
    """Check proxy behavior without real HTTP calls or database writes."""

    def setUp(self):
        """Set test-only proxy settings and create a Flask test client."""
        self.environment = patch.dict(os.environ, {
            "STATISTICS_API_URL": "http://127.0.0.1:5001",
            "STATISTICS_TIMEOUT_SECONDS": "2",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = tasks.app.test_client()

    def response(self, payload):
        """Build a fake successful response with a JSON body."""
        upstream = MagicMock()
        upstream.__enter__.return_value = upstream
        upstream.status = 200
        upstream.read.return_value = json.dumps(payload).encode()
        return upstream

    def test_proxy_contract_and_fixed_destination(self):
        """Check the destination, timeout, counters, and lack of database calls."""
        counts = {"total": 3, "completed": 1, "pending": 2}
        with patch.object(tasks, "build_opener") as opener, patch.object(tasks, "query") as query:
            opener.return_value.open.return_value = self.response(counts)
            response = self.client.get("/api/statistics")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, counts)
            call = opener.return_value.open.call_args
            self.assertEqual(call.args[0].full_url, "http://127.0.0.1:5001/api/statistics")
            self.assertEqual(call.kwargs["timeout"], 2)
            query.assert_not_called()

    def test_tasks_listing_does_not_call_statistics(self):
        """Keep task listing separate so statistics calls cannot loop."""
        with patch.object(tasks, "query", return_value=[]), patch.object(tasks, "build_opener") as opener:
            self.assertEqual(self.client.get("/api/tasks").json, [])
            opener.assert_not_called()

    def test_invalid_statistics(self):
        """Reject bad counters, invalid JSON, and oversized responses."""
        cases = [[], {}, {"total": 1, "completed": True, "pending": 0},
                 {"total": 1, "completed": 2, "pending": -1},
                 {"total": 3, "completed": 1, "pending": 1}]
        for payload in cases:
            with self.subTest(payload=payload), patch.object(tasks, "build_opener") as opener:
                opener.return_value.open.return_value = self.response(payload)
                response = self.client.get("/api/statistics")
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json, {"error": "Statistics service returned invalid data."})
        for body in (b"not json", b"\xff", b"x" * 65_537):
            with patch.object(tasks, "build_opener") as opener:
                upstream = self.response({})
                upstream.read.return_value = body
                opener.return_value.open.return_value = upstream
                self.assertEqual(self.client.get("/api/statistics").status_code, 502)

    def test_safe_upstream_errors(self):
        """Return safe errors without private upstream details."""
        # Simulate failures instead of stopping a real service.
        cases = [(URLError("private detail"), 503), (socket.timeout("private detail"), 504),
                 (URLError(socket.timeout()), 504)]
        for code in (302, 500, 502, 503, 504):
            cases.append((HTTPError("http://private", code, "private detail", {}, io.BytesIO()),
                          code if code in (502, 504) else 503))
        for error, status in cases:
            with self.subTest(status=status), patch.object(tasks, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                response = self.client.get("/api/statistics")
                self.assertEqual(response.status_code, status)
                self.assertNotIn("private", response.get_data(as_text=True))

    def test_invalid_configuration(self):
        """Reject unsafe or malformed Statistics addresses before any request."""
        for url in ("http://host/api/statistics", "http://user:password@host", "file:///tmp/test", "http://[bad"):
            with patch.dict(os.environ, {"STATISTICS_API_URL": url}), patch.object(tasks, "build_opener") as opener:
                self.assertEqual(self.client.get("/api/statistics").status_code, 503)
                opener.assert_not_called()

    def test_redirects_are_not_followed(self):
        """Refuse redirects that could send the proxy to another endpoint."""
        handler = tasks.NoStatisticsRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "", {}, "http://127.0.0.1:5000/api/statistics"))


if __name__ == "__main__":
    unittest.main(verbosity=2)