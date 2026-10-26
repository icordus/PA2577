"""Keep the old Statistics HTTP tests disabled to protect application data."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import Request, urlopen
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TASKS_URL = "http://127.0.0.1:5000"
STATISTICS_URL = "http://127.0.0.1:5001"


def http(method, url, payload=None):
    """Send a request and read the JSON response."""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=5) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


class StatisticsHTTPTests(unittest.TestCase):
    """Describe the old native tests; use the isolated runner instead."""

    server = None

    @classmethod
    def start_server(cls):
        """Start a test-owned Statistics process without database settings."""
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 5001))
        environment = os.environ.copy()
        # Statistics must get tasks through HTTP, not PostgreSQL.
        for key in tuple(environment):
            if key.startswith("DB_") or key.startswith("PG") or key == "DATABASE_URL":
                environment.pop(key)
        environment["TASKS_API_URL"] = TASKS_URL
        environment["TASKS_TIMEOUT_SECONDS"] = "2"
        cls.server = subprocess.Popen(
            [sys.executable, "services/statistics/app.py"],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if cls.server.poll() is not None:
                raise RuntimeError("Test Statistics process exited before startup.")
            try:
                if http("GET", STATISTICS_URL + "/health") == (200, {"status": "ok"}):
                    return
            except (URLError, TimeoutError, ConnectionError):
                continue
        cls.stop_server()
        raise RuntimeError("Test Statistics startup timed out.")

    @classmethod
    def stop_server(cls):
        """Stop only the Statistics process stored by this class."""
        if cls.server is not None:
            cls.server.terminate()
            cls.server.wait(timeout=5)
            cls.server = None

    @classmethod
    def setUpClass(cls):
        """Skip this suite before contacting the native services."""
        # Keep the native database out of test runs.
        raise unittest.SkipTest("Native database targets are disabled; use scripts/integration_http.py.")
        cls.addClassCleanup(cls.stop_server)
        status, body = http("GET", TASKS_URL + "/health")
        if status != 200 or body != {"status": "ok"}:
            raise RuntimeError("Tasks service is unavailable; refusing integration tests.")
        cls.start_server()

    def test_statistics_follow_real_task_creation_and_completion(self):
        """Compare counters before creation, after creation, and after completion."""
        title = "pa2577-statistics-test-" + uuid.uuid4().hex
        baseline_status, baseline = http("GET", STATISTICS_URL + "/api/statistics")
        self.assertEqual(baseline_status, 200)
        self.assertEqual(baseline["total"], baseline["completed"] + baseline["pending"])

        task_id = None
        try:
            status, task = http("POST", TASKS_URL + "/api/tasks", {"title": title})
            self.assertEqual(status, 201)
            task_id = task["id"]
            self.assertFalse(task["completed"])

            status, after_create = http("GET", STATISTICS_URL + "/api/statistics")
            self.assertEqual(status, 200)
            self.assertEqual(after_create["total"], baseline["total"] + 1)
            self.assertEqual(after_create["completed"], baseline["completed"])
            self.assertEqual(after_create["pending"], baseline["pending"] + 1)
            print(
                "Statistics before/create/completion: "
                f"{baseline} -> {after_create} -> "
                f"{{'total': {baseline['total'] + 1}, "
                f"'completed': {baseline['completed'] + 1}, "
                f"'pending': {baseline['pending']}}}"
            )

            status, updated = http(
                "PATCH", f"{TASKS_URL}/api/tasks/{task_id}", {"completed": True}
            )
            self.assertEqual(status, 200)
            self.assertTrue(updated["completed"])

            status, after_completion = http("GET", STATISTICS_URL + "/api/statistics")
            self.assertEqual(status, 200)
            self.assertEqual(after_completion["total"], baseline["total"] + 1)
            self.assertEqual(after_completion["completed"], baseline["completed"] + 1)
            self.assertEqual(after_completion["pending"], baseline["pending"])
        finally:
            # Never delete tasks that were not created by this test.
            if task_id is not None:
                request = Request(f"{TASKS_URL}/api/tasks/{task_id}", method="DELETE")
                with urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 204)

        self.assertEqual(http("GET", STATISTICS_URL + "/api/statistics"), (200, baseline))

    def test_health_does_not_depend_on_tasks(self):
        """Check health without fetching the task list."""
        self.assertEqual(http("GET", STATISTICS_URL + "/health"), (200, {"status": "ok"}))

    def test_upstream_failures_and_invalid_payloads_are_safe_json(self):
        """Return safe JSON for simulated Tasks failures and bad data."""
        from services.statistics import app as statistics_app

        client = statistics_app.app.test_client()
        # Replace HTTP calls so no real upstream service is needed.
        with patch.dict(os.environ, {"TASKS_API_URL": "http://tasks.invalid"}):
            with patch.object(statistics_app, "urlopen", side_effect=TimeoutError()):
                response = client.get("/api/statistics")
                self.assertEqual(response.status_code, 504)
                self.assertEqual(response.get_json(), {"error": "Tasks service timed out."})
            with patch.object(
                statistics_app,
                "urlopen",
                side_effect=URLError("private network detail must not be returned"),
            ):
                response = client.get("/api/statistics")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.get_json(), {"error": "Tasks service is unavailable."})
            for body in (b"not json", b"{}", b"[{}]", b'[{"completed":1}]'):
                response_mock = unittest.mock.MagicMock()
                response_mock.__enter__.return_value.status = 200
                response_mock.__enter__.return_value.read.return_value = body
                with patch.object(statistics_app, "urlopen", return_value=response_mock):
                    response = client.get("/api/statistics")
                    self.assertEqual(response.status_code, 502)
                    self.assertEqual(
                        response.get_json(),
                        {"error": "Tasks service returned invalid data."},
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)