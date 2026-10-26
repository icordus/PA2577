"""Test real HTTP flows only in the isolated integration environment."""

import json
import time
import unittest
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import uuid


class NoRedirect(HTTPRedirectHandler):
    """Keep requests on the approved test target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Refuse HTTP redirects."""
        return None


class IsolatedHTTPTests(unittest.TestCase):
    """Use only containers configured by the isolated runner."""

    base_url = None
    run_id = None
    target_guard = None
    statistics_control = None

    @classmethod
    def setUpClass(cls):
        """Require the runner's target and safety checks before any request."""
        if cls.base_url is None or cls.target_guard is None or cls.statistics_control is None:
            raise unittest.SkipTest("Only scripts/integration_http.py may configure isolated targets.")
        cls.target_guard()

    def setUp(self):
        """Give each test a unique marker and its own cleanup list."""
        self.created_ids = set()
        self.marker = f"pa2577-it-{self.run_id}-{uuid.uuid4().hex}"

    def http(self, method, path, payload=None, raw=None):
        """Send a request to the isolated target and record created IDs."""
        if method not in {"GET", "POST", "PATCH", "DELETE"} or not path.startswith("/") or path.startswith("//"):
            raise ValueError("Unexpected integration request.")
        # Recheck ownership before requests that can change data.
        if method != "GET":
            self.target_guard()
        data = json.dumps(payload).encode() if payload is not None else raw
        request = Request(
            self.base_url + path, data=data, method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        # Ignore system proxies and do not follow redirects.
        opener = build_opener(ProxyHandler({}), NoRedirect())
        try:
            response = opener.open(request, timeout=8)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            result = json.loads(body) if body else None
            if method == "POST" and response.status == 201 and isinstance(result, dict):
                self.created_ids.add(result["id"])
            return response.status, result

    def tearDown(self):
        """Delete only this test's tasks and check that they are gone."""
        for task_id in sorted(self.created_ids):
            status, _ = self.http("DELETE", f"/api/tasks/{task_id}")
            self.assertIn(status, (204, 404))
        status, tasks = self.http("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertFalse(any(task["id"] in self.created_ids for task in tasks))

    def create(self, title=None, **fields):
        """Create a task with this test's marker unless a title is given."""
        status, task = self.http("POST", "/api/tasks", {"title": title or self.marker, **fields})
        self.assertEqual(status, 201)
        return task

    def test_create_list_statistics_complete_delete(self):
        """Check the full task flow and its effect on the counters."""
        self.assertEqual(self.http("GET", "/health"), (200, {"status": "ok"}))
        self.assertEqual(self.http("GET", "/ready"), (200, {"status": "ok"}))
        status, before = self.http("GET", "/api/statistics")
        self.assertEqual(status, 200)
        task = self.create()
        self.assertFalse(task["completed"])
        self.assertIn(task, self.http("GET", "/api/tasks")[1])
        self.assertEqual(self.http("GET", "/api/statistics"), (200, {
            "total": before["total"] + 1, "completed": before["completed"], "pending": before["pending"] + 1,
        }))
        status, updated = self.http("PATCH", f"/api/tasks/{task['id']}", {"completed": True})
        self.assertEqual(status, 200)
        self.assertTrue(updated["completed"])
        self.assertEqual(updated["created_at"], task["created_at"])
        self.assertEqual(self.http("GET", "/api/statistics"), (200, {
            "total": before["total"] + 1, "completed": before["completed"] + 1, "pending": before["pending"],
        }))
        self.assertEqual(self.http("DELETE", f"/api/tasks/{task['id']}"), (204, None))
        self.assertEqual(self.http("GET", "/api/statistics"), (200, before))

    def test_validation_parameterization_and_missing_ids(self):
        """Check title limits, bad input, SQL-like text, and missing IDs."""
        title = self.marker + " '; DROP TABLE tasks.tasks; --"
        task = self.create(title="  " + title + "  ")
        self.assertEqual(task["title"], title)
        boundary = self.create(title=self.marker.ljust(200, "x"), completed=True)
        self.assertEqual(len(boundary["title"]), 200)
        invalid = [{}, [], "invalid", {"title": None}, {"title": 1}, {"title": " \t\n"},
                   {"title": "x" * 201}, {"title": "bad\u0000title"},
                   {"title": self.marker, "completed": "true"}, {"title": self.marker, "completed": 1},
                   {"title": self.marker, "completed": None}, {"title": self.marker, "unknown": True}]
        for payload in invalid:
            for method, path in (("POST", "/api/tasks"), ("PATCH", f"/api/tasks/{task['id']}")):
                with self.subTest(method=method, payload=payload):
                    status, body = self.http(method, path, payload)
                    self.assertEqual(status, 400)
                    self.assertIsInstance(body["error"], str)
        for raw in (b"{broken", b"null", b""):
            self.assertEqual(self.http("POST", "/api/tasks", raw=raw)[0], 400)
        for task_id in (0, 9223372036854775808):
            self.assertEqual(self.http("PATCH", f"/api/tasks/{task_id}", {"completed": True})[0], 404)
            self.assertEqual(self.http("DELETE", f"/api/tasks/{task_id}")[0], 404)
        self.assertIn(task, self.http("GET", "/api/tasks")[1])

    def test_statistics_failure_is_safe_and_tasks_remain_available(self):
        """Keep Tasks usable while the test's Statistics container is stopped."""
        # This controls only the temporary container owned by the test run.
        self.statistics_control("stop")
        try:
            self.assertEqual(self.http("GET", "/api/statistics"),
                             (503, {"error": "Statistics service is unavailable."}))
            self.assertEqual(self.http("GET", "/health"), (200, {"status": "ok"}))
            self.assertEqual(self.http("GET", "/ready"), (200, {"status": "ok"}))
            self.assertEqual(self.http("GET", "/api/tasks")[0], 200)
        finally:
            # Restore Statistics even if an assertion fails.
            self.statistics_control("start")
        deadline = time.monotonic() + 30
        while self.http("GET", "/api/statistics")[0] != 200:
            if time.monotonic() >= deadline:
                self.fail("Temporary Statistics did not recover.")


if __name__ == "__main__":
    unittest.main(verbosity=2)