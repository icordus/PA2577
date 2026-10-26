"""Keep the old Tasks HTTP tests disabled to protect application data."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:5000"


def http(method, path, payload=None, raw=None):
    """Send a request and return its status and JSON body."""
    data = json.dumps(payload).encode() if payload is not None else raw
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        body = response.read()
        return response.status, json.loads(body) if body else None


class TasksHTTPTests(unittest.TestCase):
    """Describe the old native tests; use the isolated runner instead."""

    server = None

    @classmethod
    def start_server(cls, overrides=None):
        """Start a test-owned Flask process and wait for health."""
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 5000))
        environment = os.environ.copy()
        environment.update(overrides or {})
        cls.server = subprocess.Popen(
            [sys.executable, "services/tasks/app.py"],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if cls.server.poll() is not None:
                raise RuntimeError("Test Flask process exited before startup.")
            try:
                if http("GET", "/health") == (200, {"status": "ok"}):
                    return
            except (URLError, TimeoutError, ConnectionError):
                continue
        cls.stop_server()
        raise RuntimeError("Test Flask startup timed out.")

    @classmethod
    def stop_server(cls):
        """Stop only the Flask process stored by this class."""
        if cls.server is not None:
            cls.server.terminate()
            cls.server.wait(timeout=5)
            cls.server = None

    @classmethod
    def setUpClass(cls):
        """Skip this suite before starting a server or changing data."""
        # Keep the native database out of test runs.
        raise unittest.SkipTest("Native database targets are disabled; use scripts/integration_http.py.")
        cls.addClassCleanup(cls.stop_server)
        cls.start_server()

    def setUp(self):
        """Track this test's task IDs and unique title marker."""
        self.task_ids = []
        self.marker = "pa2577-http-" + uuid.uuid4().hex

    def tearDown(self):
        """Delete only tasks recorded by this test."""
        for task_id in self.task_ids:
            status, _ = http("DELETE", f"/api/tasks/{task_id}")
            self.assertIn(status, (204, 404))

    def create(self, **changes):
        """Create a task and remember its ID for cleanup."""
        status, task = http("POST", "/api/tasks", {"title": self.marker, **changes})
        self.assertEqual(status, 201)
        self.task_ids.append(task["id"])
        return task

    def test_health_and_readiness(self):
        """Check that the service and its database are ready."""
        self.assertEqual(http("GET", "/health"), (200, {"status": "ok"}))
        self.assertEqual(http("GET", "/ready"), (200, {"status": "ok"}))

    def test_crud_and_parameterized_title(self):
        """Create, list, update, and delete a task with SQL-like text."""
        # SQL in a title must stay plain data.
        title = "  " + self.marker + " '; DROP TABLE tasks.tasks; --  "
        task = self.create(title=title)
        self.assertEqual(task["title"], title.strip())
        self.assertFalse(task["completed"])
        self.assertIsInstance(task["id"], int)
        self.assertTrue(task["created_at"].endswith("+00:00"))
        status, tasks = http("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertIn(task, tasks)
        path = f"/api/tasks/{task['id']}"
        status, updated = http("PATCH", path, {"completed": True})
        self.assertEqual(status, 200)
        self.assertTrue(updated["completed"])
        self.assertEqual(updated["title"], task["title"])
        status, updated = http("PATCH", path, {"title": self.marker, "completed": False})
        self.assertEqual(status, 200)
        self.assertFalse(updated["completed"])
        self.assertEqual(updated["title"], self.marker)
        self.assertEqual(updated["created_at"], task["created_at"])
        self.assertEqual(http("DELETE", path), (204, None))
        self.assertEqual(http("PATCH", path, {"completed": True})[0], 404)
        self.assertEqual(http("DELETE", path)[0], 404)

    def test_creation_with_completed_and_title_boundary(self):
        """Accept a completed task with a 200-character title."""
        task = self.create(title="x" * 200, completed=True)
        self.assertTrue(task["completed"])
        self.assertEqual(len(task["title"]), 200)

    def test_invalid_post_and_patch_leave_record_unchanged(self):
        """Reject bad input without changing the saved task."""
        task = self.create()
        invalid = [
            {}, [], "string", {"title": None}, {"title": 42},
            {"title": " \t\n"}, {"title": "x" * 201}, {"title": "bad\u0000title"},
            {"title": "valid", "completed": "true"},
            {"title": "valid", "completed": 1},
            {"title": "valid", "completed": None},
            {"title": "valid", "unknown": "field"},
        ]
        for payload in invalid:
            for method, path in (
                ("POST", "/api/tasks"),
                ("PATCH", f"/api/tasks/{task['id']}"),
            ):
                with self.subTest(method=method, payload=payload):
                    status, body = http(method, path, payload)
                    self.assertEqual(status, 400)
                    self.assertIsInstance(body["error"], str)
        self.assertEqual(http("POST", "/api/tasks", {"completed": True})[0], 400)
        for raw in (b"{broken", b"null", b""):
            self.assertEqual(http("POST", "/api/tasks", raw=raw)[0], 400)
        self.assertIn(task, http("GET", "/api/tasks")[1])

    def test_missing_ids(self):
        """Return not found for missing or oversized task IDs."""
        for task_id in (0, 9223372036854775808):
            path = f"/api/tasks/{task_id}"
            self.assertEqual(http("PATCH", path, {"completed": True})[0], 404)
            self.assertEqual(http("DELETE", path)[0], 404)

    def test_persistence_across_flask_restart(self):
        """Keep the task after restarting only Flask."""
        task = self.create()
        self.stop_server()
        self.start_server()
        status, tasks = http("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertIn(task, tasks)

    def test_unavailable_database_is_safe(self):
        """Return safe errors when the test server cannot reach its database."""
        self.stop_server()
        try:
            # Change the test connection, not PostgreSQL itself.
            self.start_server({"DB_PORT": "1"})
            self.assertEqual(http("GET", "/health"), (200, {"status": "ok"}))
            for method, path, payload in (
                ("GET", "/ready", None),
                ("GET", "/api/tasks", None),
                ("POST", "/api/tasks", {"title": self.marker}),
                ("PATCH", "/api/tasks/1", {"completed": True}),
                ("DELETE", "/api/tasks/1", None),
            ):
                self.assertEqual(http(method, path, payload), (503, {"error": "Database unavailable."}))
        finally:
            self.stop_server()
            self.start_server()


if __name__ == "__main__":
    unittest.main(verbosity=2)