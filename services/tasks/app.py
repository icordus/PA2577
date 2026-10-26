"""Serve the task API, web page, and statistics proxy."""

import json
import os
from pathlib import Path
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import psycopg
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, url_for
from psycopg.rows import dict_row


# Keep existing environment values when loading local settings.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
app = Flask(__name__)


class DatabaseConfigurationError(Exception):
    """Report missing or unexpected database settings."""

    pass


class NoStatisticsRedirect(HTTPRedirectHandler):
    """Keep statistics requests on the configured endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Refuse HTTP redirects."""
        return None


def statistics_error(message, status):
    """Return a JSON error with the given HTTP status."""
    return jsonify(error=message), status


@app.get("/api/statistics")
def statistics_proxy():
    """Fetch and check counters from Statistics for the browser."""
    try:
        base_url = os.environ.get("STATISTICS_API_URL", "http://127.0.0.1:5001")
        parsed = urlsplit(base_url)
        parsed.port
        timeout = float(os.environ.get("STATISTICS_TIMEOUT_SECONDS", "3"))
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or not 0 < timeout <= 10
        ):
            raise ValueError()
        upstream = Request(base_url.rstrip("/") + "/api/statistics", headers={"Accept": "application/json"})
        with build_opener(NoStatisticsRedirect()).open(upstream, timeout=timeout) as response:
            if response.status != 200:
                return statistics_error("Statistics service is unavailable.", 503)
            body = response.read(65_537)
        if len(body) > 65_536:
            return statistics_error("Statistics service returned invalid data.", 502)
        data = json.loads(body)
        # Accept only non-negative counts that add up correctly.
        if (
            not isinstance(data, dict)
            or set(data) != {"total", "completed", "pending"}
            or any(type(value) is not int or value < 0 for value in data.values())
            or data["total"] != data["completed"] + data["pending"]
        ):
            return statistics_error("Statistics service returned invalid data.", 502)
        return jsonify(data)
    except HTTPError as error:
        if error.code == 504:
            return statistics_error("Statistics service timed out.", 504)
        if error.code == 502:
            return statistics_error("Statistics service returned invalid data.", 502)
        return statistics_error("Statistics service is unavailable.", 503)
    except (TimeoutError, socket.timeout):
        return statistics_error("Statistics service timed out.", 504)
    except URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            return statistics_error("Statistics service timed out.", 504)
        return statistics_error("Statistics service is unavailable.", 503)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return statistics_error("Statistics service returned invalid data.", 502)
    except (OSError, ValueError):
        return statistics_error("Statistics service is unavailable.", 503)


def query(statement, parameters=(), many=False):
    """Run SQL as the Tasks role and return one row or all rows."""
    # Do not let the application use the administrator account.
    if (
        os.environ.get("DB_USER") != "pa2577_tasks"
        or os.environ.get("DB_NAME") != "pa2577"
        or not os.environ.get("DB_PASSWORD")
    ):
        raise DatabaseConfigurationError()
    with psycopg.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=os.environ.get("DB_PORT", "55432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=3,
        options="-c statement_timeout=5000 -c timezone=UTC",
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            # Pass values separately from the SQL statement.
            cursor.execute(statement, parameters)
            return cursor.fetchall() if many else cursor.fetchone()


def serialize(task):
    """Convert the task timestamp to text for JSON."""
    return {**task, "created_at": task["created_at"].isoformat()}


def validate_payload(partial=False):
    """Check task fields and trim the title when it is present."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return None, "Expected a non-empty JSON object."
    if payload.keys() - {"title", "completed"}:
        return None, "Only title and completed are accepted."
    if not partial and "title" not in payload:
        return None, "title is required."
    if "title" in payload:
        if not isinstance(payload["title"], str):
            return None, "title must be a string."
        payload["title"] = payload["title"].strip()
        if not 1 <= len(payload["title"]) <= 200 or "\x00" in payload["title"]:
            return None, "title must contain 1 to 200 characters and no null character."
    if "completed" in payload and not isinstance(payload["completed"], bool):
        return None, "completed must be a JSON boolean."
    return payload, None


@app.errorhandler(psycopg.Error)
@app.errorhandler(DatabaseConfigurationError)
def database_unavailable(error):
    """Hide database details and return a safe unavailable response."""
    app.logger.warning("Tasks database operation failed.")
    return jsonify(error="Database unavailable."), 503


@app.get("/")
def index():
    """Serve the Task Manager web page."""
    return render_template("index.html")


@app.get("/health")
def health():
    """Report that Tasks is running without checking PostgreSQL."""
    return jsonify(status="ok")


@app.get("/ready")
def ready():
    """Check that Tasks can read its database table."""
    query("SELECT id FROM tasks.tasks LIMIT 1")
    return jsonify(status="ok")


@app.get("/api/tasks")
def list_tasks():
    """Return tasks in ID order without calling Statistics."""
    tasks = query("SELECT id, title, completed, created_at FROM tasks.tasks ORDER BY id", many=True)
    return jsonify([serialize(task) for task in tasks])


@app.post("/api/tasks")
def create_task():
    """Validate and save a new task."""
    payload, error = validate_payload()
    if error:
        return jsonify(error=error), 400
    task = query(
        "INSERT INTO tasks.tasks (title, completed) VALUES (%s, %s) "
        "RETURNING id, title, completed, created_at",
        (payload["title"], payload.get("completed", False)),
    )
    return jsonify(serialize(task)), 201, {"Location": url_for("update_task", task_id=task["id"])}


@app.patch("/api/tasks/<int:task_id>")
def update_task(task_id):
    """Update the supplied fields of an existing task."""
    payload, error = validate_payload(partial=True)
    if error:
        return jsonify(error=error), 400
    if task_id > 9223372036854775807:
        return jsonify(error="Task not found."), 404
    # Leave each field unchanged when it is not supplied.
    task = query(
        "UPDATE tasks.tasks SET title = COALESCE(%s, title), "
        "completed = COALESCE(%s, completed) WHERE id = %s "
        "RETURNING id, title, completed, created_at",
        (payload.get("title"), payload.get("completed"), task_id),
    )
    if task is None:
        return jsonify(error="Task not found."), 404
    return jsonify(serialize(task))


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    """Delete one task or return not found."""
    if task_id > 9223372036854775807:
        return jsonify(error="Task not found."), 404
    task = query("DELETE FROM tasks.tasks WHERE id = %s RETURNING id", (task_id,))
    if task is None:
        return jsonify(error="Task not found."), 404
    return "", 204


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)