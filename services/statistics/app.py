"""Calculate task counts through HTTP without database access."""

import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from flask import Flask, jsonify


app = Flask(__name__)


class TasksUnavailable(Exception):
    """Report that Tasks cannot be reached or has failed."""

    pass


class TasksTimeout(Exception):
    """Report that Tasks did not respond in time."""

    pass


class InvalidTasksResponse(Exception):
    """Report task data that cannot be used for statistics."""

    pass


def configured_tasks_url():
    """Check the Tasks address and timeout from the environment."""
    base_url = os.environ.get("TASKS_API_URL", "http://127.0.0.1:5000").rstrip("/")
    try:
        parsed = urlsplit(base_url)
        parsed.port
    except ValueError as error:
        raise TasksUnavailable() from error
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise TasksUnavailable()
    try:
        timeout = float(os.environ.get("TASKS_TIMEOUT_SECONDS", "3"))
    except ValueError as error:
        raise TasksUnavailable() from error
    if not 0 < timeout <= 30:
        raise TasksUnavailable()
    return base_url + "/api/tasks", timeout


def fetch_tasks():
    """Fetch the task list over HTTP and check its format."""
    url, timeout = configured_tasks_url()
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise TasksUnavailable()
            body = response.read(1_048_577)
    except HTTPError as error:
        raise TasksUnavailable() from error
    except (TimeoutError, socket.timeout) as error:
        raise TasksTimeout() from error
    except URLError as error:
        if isinstance(error.reason, (TimeoutError, socket.timeout)):
            raise TasksTimeout() from error
        raise TasksUnavailable() from error
    except OSError as error:
        raise TasksUnavailable() from error
    if len(body) > 1_048_576:
        raise InvalidTasksResponse()
    try:
        tasks = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise InvalidTasksResponse() from error
    # Each task must have a real boolean completion value.
    if not isinstance(tasks, list) or any(
        not isinstance(task, dict) or type(task.get("completed")) is not bool
        for task in tasks
    ):
        raise InvalidTasksResponse()
    return tasks


@app.get("/health")
def health():
    """Report that Statistics is running without contacting Tasks."""
    return jsonify(status="ok")


@app.get("/api/statistics")
def statistics():
    """Return total, completed, and pending counts or a safe JSON error."""
    try:
        tasks = fetch_tasks()
    except TasksTimeout:
        return jsonify(error="Tasks service timed out."), 504
    except TasksUnavailable:
        return jsonify(error="Tasks service is unavailable."), 503
    except InvalidTasksResponse:
        return jsonify(error="Tasks service returned invalid data."), 502
    completed = sum(task["completed"] for task in tasks)
    total = len(tasks)
    return jsonify(total=total, completed=completed, pending=total - completed)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)