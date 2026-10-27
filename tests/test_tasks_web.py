"""Test the server-rendered Tasks page and proxy without external services."""

from datetime import datetime, timezone
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


class ServerRenderedTasksTests(unittest.TestCase):
    """Check HTML forms and unchanged JSON APIs with mocked dependencies."""

    def setUp(self):
        """Use a fake task, database queries, and Statistics response."""
        self.client = tasks.app.test_client()
        self.task = {"id": 7, "title": "Example task", "completed": False,
                     "created_at": datetime(2026, 10, 27, tzinfo=timezone.utc)}
        self.origin = {"Origin": "http://localhost"}
        database = patch.object(tasks, "query", return_value=[self.task])
        self.query = database.start()
        self.addCleanup(database.stop)
        upstream = patch.object(tasks, "statistics_proxy",
                                side_effect=lambda: tasks.jsonify(total=1, completed=0, pending=1))
        self.statistics = upstream.start()
        self.addCleanup(upstream.stop)

    def test_page_renders_tasks_statistics_and_forms_without_scripts(self):
        """Render usable forms, counters, and the task list without JavaScript."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for value in ('value="Example task"', 'id="total">1', 'action="/tasks/create"',
                      'action="/tasks/7/update"', 'action="/tasks/7/delete"'):
            self.assertIn(value, html)
        self.assertNotIn("<script", html)
        self.assertNotIn("tasks.js", html)
        self.query.assert_called_once()
        self.statistics.assert_called_once()

    def test_titles_are_escaped_in_html_attributes(self):
        """Keep HTML-like titles as text rather than executable markup."""
        self.task["title"] = '\"><script>alert("test")</script>'
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script", html)

    def test_create_form_redirects_after_saving(self):
        """Trim a title and redirect after one insert without repeating a POST."""
        self.query.return_value = self.task
        response = self.client.post("/tasks/create", data={"title": "  Example task  "}, headers=self.origin)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/")
        self.assertEqual(self.query.call_args.args[1], ("Example task", False))

    def test_update_form_saves_title_and_both_completion_states(self):
        """Handle checked and unchecked HTML checkboxes without JavaScript."""
        self.query.return_value = self.task
        for completed in (False, True):
            with self.subTest(completed=completed):
                payload = {"title": "Edited title"}
                if completed:
                    payload["completed"] = "on"
                response = self.client.post("/tasks/7/update", data=payload, headers=self.origin)
                self.assertEqual(response.status_code, 303)
                self.assertEqual(self.query.call_args.args[1], ("Edited title", completed, 7))

    def test_delete_form_redirects_after_removal(self):
        """Delete only the selected ID and return to the page."""
        self.query.return_value = {"id": 7}
        response = self.client.post("/tasks/7/delete", headers=self.origin)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.query.call_args.args[1], (7,))

    def test_form_errors_render_html_without_a_write(self):
        """Show validation errors in the page without inserting a task."""
        response = self.client.post("/tasks/create", data={"title": "   "}, headers=self.origin)
        self.assertEqual(response.status_code, 400)
        self.assertIn("title must contain", response.get_data(as_text=True))
        self.assertEqual(self.query.call_count, 1)
        self.assertTrue(self.query.call_args.kwargs["many"])

    def test_forms_reject_cross_origin_and_missing_origin(self):
        """Reject unsafe form submissions before touching the database."""
        for origin in ({}, {"Origin": "http://other.example"}, {"Origin": "null"}):
            for path in ("/tasks/create", "/tasks/7/update", "/tasks/7/delete"):
                with self.subTest(origin=origin, path=path):
                    self.assertEqual(self.client.post(path, headers=origin).status_code, 403)
        self.query.assert_not_called()

    def test_database_failure_renders_safe_html(self):
        """Report database failure without showing configuration details."""
        self.query.side_effect = tasks.DatabaseConfigurationError()
        for method, path in (("GET", "/"), ("POST", "/tasks/7/delete")):
            with self.subTest(path=path):
                response = self.client.open(path, method=method, headers=self.origin)
                self.assertEqual(response.status_code, 503)
                self.assertIn("Database unavailable.", response.get_data(as_text=True))

    def test_statistics_failure_keeps_task_list_available(self):
        """Retain tasks and mark counters unavailable when Statistics fails."""
        self.statistics.side_effect = lambda: (tasks.jsonify(error="Statistics service is unavailable."), 503)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('value="Example task"', html)
        self.assertIn('id="total">--', html)
        self.assertIn("Statistics service is unavailable.", html)

    def test_json_crud_contract_is_unchanged(self):
        """Preserve JSON, Location headers, and status codes for API clients."""
        self.query.return_value = self.task
        response = self.client.post("/api/tasks", json={"title": "Example task"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["id"], 7)
        self.assertEqual(response.headers["Location"], "/api/tasks/7")
        response = self.client.patch("/api/tasks/7", json={"completed": True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        response = self.client.delete("/api/tasks/7")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b"")
        self.assertEqual(self.client.post("/api/tasks", data={"title": "Not JSON"}).status_code, 400)

    def test_missing_task_remains_not_found_for_api_and_forms(self):
        """Return 404 for absent IDs in both interfaces."""
        self.query.side_effect = lambda statement, parameters=(), many=False: [] if many else None
        response = self.client.post("/tasks/7/delete", headers=self.origin)
        self.assertEqual(response.status_code, 404)
        self.assertIn("Task not found.", response.get_data(as_text=True))
        response = self.client.delete("/api/tasks/7")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {"error": "Task not found."})


if __name__ == "__main__":
    unittest.main(verbosity=2)