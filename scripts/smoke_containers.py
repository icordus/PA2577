"""Check isolated application images without using the existing database."""

import json
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import uuid


ROOT = Path(__file__).resolve().parents[1]


def docker(*arguments):
    """Run a Docker command and return its text output."""
    return subprocess.check_output(["docker", *arguments], text=True).strip()


def existing_postgres():
    """Read container identity, start time, and mount metadata only."""
    return docker(
        "container", "inspect", "--format",
        "{{.Id}}|{{.State.StartedAt}}|{{.State.Running}}|"
        "{{range .Mounts}}{{.Type}}:{{.Source}}:{{.Destination}}:{{.RW}};{{end}}",
        "pa2577-postgres",
    )


def http(base_url, path):
    """Read a smoke endpoint and return its status and body."""
    try:
        response = urlopen(base_url + path, timeout=2)
    except HTTPError as error:
        response = error
    with response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "")
        return response.status, json.loads(body) if "application/json" in content_type else body


def check_service(service, network, resources):
    """Check one ARM64 image in a temporary non-root container."""
    image = f"pa2577-{service}:todo5-smoke"
    metadata = json.loads(docker("image", "inspect", image))[0]
    assert metadata["Os"] == "linux" and metadata["Architecture"] == "arm64"
    assert metadata["Config"]["User"] == "10001:10001"
    assert metadata["Config"]["Cmd"][0] == "gunicorn"
    assert metadata["Config"]["Healthcheck"]["Test"][0] == "CMD"
    name = f"pa2577-smoke-{service}-{uuid.uuid4().hex[:12]}"
    resources.append(name)
    # Give Docker a free loopback port; do not mount data or pass secrets.
    docker(
        "run", "--detach", "--pull", "never", "--name", name,
        "--label", "project=pa2577-todo5-smoke", "--platform", "linux/arm64",
        "--network", network, "--publish", "127.0.0.1::8000",
        "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges=true",
        "--memory", "256m", "--cpus", "1", "--pids-limit", "64",
        "--env", "STATISTICS_API_URL=http://127.0.0.1:9",
        "--env", "TASKS_API_URL=http://127.0.0.1:9",
        image,
    )
    container = json.loads(docker("container", "inspect", name))[0]
    ports = container["NetworkSettings"]["Ports"]
    assert set(ports) == {"8000/tcp"}, ports
    assert len(ports["8000/tcp"]) == 1
    binding = ports["8000/tcp"][0]
    assert binding["HostIp"] == "127.0.0.1"
    assert container["HostConfig"]["ReadonlyRootfs"]
    assert all(mount["Type"] == "tmpfs" for mount in container["Mounts"])
    assert not container["HostConfig"]["Privileged"]
    assert "ALL" in container["HostConfig"]["CapDrop"]
    assert not any(entry.startswith("DB_") for entry in container["Config"]["Env"])
    base_url = "http://127.0.0.1:" + binding["HostPort"]
    # Allow the application time to start before checking its endpoints.
    deadline = time.monotonic() + 15
    while True:
        try:
            assert http(base_url, "/health") == (200, {"status": "ok"})
            break
        except (URLError, TimeoutError, ConnectionError):
            if time.monotonic() >= deadline:
                raise RuntimeError("Container health startup timed out.") from None
    # Check the actual process user and files inside the image.
    validation = (
        "import importlib.util, os; from pathlib import Path; "
        f"from services.{service}.app import app; "
        "assert os.getuid() == 10001 and os.getgid() == 10001; "
        "assert app.debug is False; "
        "assert not any(path.name in {'.env', '.secrets', '.git', '.venv'} "
        "for path in Path('/app').rglob('*')); "
        "assert b'gunicorn' in Path('/proc/1/cmdline').read_bytes(); "
        "print('PASS: non-root, Gunicorn PID 1, debug off, no project secrets')"
    )
    if service == "statistics":
        validation += (
            "; assert importlib.util.find_spec('psycopg') is None; "
            "assert importlib.util.find_spec('dotenv') is None"
        )
    print(docker("exec", name, "python", "-B", "-c", validation))
    healthcheck = metadata["Config"]["Healthcheck"]["Test"][1:]
    docker("exec", name, *healthcheck)
    docker("exec", name, "python", "-m", "pip", "check")
    # Missing dependencies should produce safe errors, not real data calls.
    if service == "tasks":
        assert http(base_url, "/")[0] == 200
        assert http(base_url, "/static/tasks.js")[0] == 200
        assert http(base_url, "/static/tasks.css")[0] == 200
        for path in ("/ready", "/api/tasks"):
            assert http(base_url, path) == (503, {"error": "Database unavailable."})
        assert http(base_url, "/api/statistics") == (
            503, {"error": "Statistics service is unavailable."}
        )
    else:
        assert http(base_url, "/api/statistics") == (
            503, {"error": "Tasks service is unavailable."}
        )
    print(f"PASS: {service} ARM64, {base_url}, healthcheck, safe dependency errors")


def main():
    """Run image checks, remove temporary resources, and compare metadata."""
    postgres_before = existing_postgres()
    network = "pa2577-smoke-" + uuid.uuid4().hex[:12]
    resources = []
    network_created = False
    try:
        docker("network", "create", "--driver", "bridge", "--label", "project=pa2577-todo5-smoke", network)
        network_created = True
        for service in ("tasks", "statistics"):
            check_service(service, network, resources)
    finally:
        # Remove only names recorded by this smoke run.
        for name in reversed(resources):
            subprocess.run(["docker", "container", "rm", "--force", name], check=True)
        if network_created:
            docker("network", "rm", network)
        # This comparison still needs review after the recorded smoke failure.
        assert existing_postgres() == postgres_before, "Existing PostgreSQL metadata changed"
    assert not docker(
        "container", "ls", "--all", "--filter", "network=" + network, "--format", "{{.ID}}"
    )
    print("PASS: only own temporary resources removed; PostgreSQL ID/start time/mounts unchanged")
    print("Full integration and persistence remain unverified until Kubernetes stages 8/9.")


if __name__ == "__main__":
    main()