"""Read-only smoke checks for the deployed PA2577 Tasks API."""

import argparse
import ipaddress
import json
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_RESPONSE_BYTES = 1_048_576


class RejectRedirects(HTTPRedirectHandler):
    """Do not let the deployment smoke test follow redirects elsewhere."""

    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def validate_base_url(base_url):
    """Accept only a private node IP and a Kubernetes NodePort URL."""
    try:
        parsed = urlsplit(base_url)
        address = ipaddress.ip_address(parsed.hostname or "")
        port = parsed.port
    except ValueError as error:
        raise ValueError("Deployment URL must use a private IP and a valid port.") from error
    if (
        parsed.scheme != "http"
        or not (address.is_private or address.is_loopback)
        or port is None
        or not 30000 <= port <= 32767
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Refusing a non-private or non-NodePort deployment URL.")
    return f"http://{address.compressed}:{port}"


def validate_responses(health, readiness, tasks, statistics):
    """Check health payloads and ensure statistics match the task list."""
    if health != {"status": "ok"} or readiness != {"status": "ok"}:
        raise ValueError("Tasks health or readiness response is invalid.")
    if not isinstance(tasks, list) or any(
        not isinstance(task, dict) or type(task.get("completed")) is not bool
        for task in tasks
    ):
        raise ValueError("Tasks API returned an invalid task list.")
    required_keys = {"total", "completed", "pending"}
    if (
        not isinstance(statistics, dict)
        or set(statistics) != required_keys
        or any(type(value) is not int or value < 0 for value in statistics.values())
    ):
        raise ValueError("Statistics API returned invalid counters.")
    completed = sum(task["completed"] for task in tasks)
    expected = {
        "total": len(tasks),
        "completed": completed,
        "pending": len(tasks) - completed,
    }
    if statistics != expected:
        raise ValueError("Statistics do not match the Tasks API response.")
    return expected


def get_json(opener, base_url, path):
    request = Request(base_url + path, headers={"Accept": "application/json"})
    try:
        with opener.open(request, timeout=10) as response:
            if response.status != 200:
                raise ValueError(f"{path} returned HTTP {response.status}.")
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                raise ValueError(f"{path} did not return JSON.")
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        raise ValueError(f"{path} returned HTTP {error.code}.") from None
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError(f"{path} returned an oversized response.")
    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"{path} returned invalid JSON.") from error


def verify_deployment(base_url):
    """Read health, readiness, task list, and statistics without mutating data."""
    base_url = validate_base_url(base_url)
    opener = build_opener(RejectRedirects())
    health = get_json(opener, base_url, "/health")
    readiness = get_json(opener, base_url, "/ready")
    tasks = get_json(opener, base_url, "/api/tasks")
    statistics = get_json(opener, base_url, "/api/statistics")
    return validate_responses(health, readiness, tasks, statistics)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args(argv)
    try:
        counts = verify_deployment(args.base_url)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(
        "PASS: deployed HTTP endpoints; "
        f"{counts['total']} tasks, {counts['completed']} completed, "
        f"{counts['pending']} pending."
    )


if __name__ == "__main__":
    main()
