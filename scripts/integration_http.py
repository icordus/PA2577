"""Plan isolated HTTP tests; create temporary resources only with --execute."""

import argparse
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from integration_safety import LABEL, require, validate_target
from test_isolated_http import IsolatedHTTPTests


def docker(*arguments, input_text=None):
    """Run Docker with optional stdin and hide sensitive error output."""
    result = subprocess.run(
        ["docker", *arguments], input=input_text, capture_output=True, text=True, timeout=120,
    )
    if result.returncode:
        raise RuntimeError(f"Docker {arguments[0]} failed; details suppressed to protect temporary credentials.")
    return result.stdout.strip()


def inspect_container(identifier):
    """Read container metadata for the supplied ID."""
    return json.loads(docker("container", "inspect", identifier))[0]


class IsolatedRun:
    """Track one temporary network and its three test containers."""

    def __init__(self, arguments):
        """Create a unique run ID without starting any resources."""
        self.arguments = arguments
        self.run_id = uuid.uuid4().hex
        self.network = "pa2577-it-" + self.run_id
        self.network_id = None
        self.containers = {}
        self.base_url = None

    def owned(self, service):
        """Refuse a container whose ID, name, or run label does not match."""
        container = inspect_container(self.containers[service])
        require(container["Id"] == self.containers[service]
                and container["Config"]["Labels"].get(LABEL) == self.run_id
                and container["Name"] == f"/{self.network}-{service}", "Refusing unowned resource.")
        return container

    def create(self, service, image, environment, *options):
        """Create and start one test container without stored data mounts."""
        # Pass temporary settings through stdin, not command arguments.
        identifier = docker(
            "container", "create", "--pull", "never", "--platform", "linux/arm64",
            "--name", f"{self.network}-{service}", "--label", f"{LABEL}={self.run_id}",
            "--network", self.network, "--network-alias", "db" if service == "postgres" else service,
            "--env-file", "/dev/stdin", "--security-opt", "no-new-privileges=true",
            "--cpus", "1", "--pids-limit", "128", *options, image,
            input_text="".join(f"{key}={value}\n" for key, value in environment.items()),
        )
        self.containers[service] = identifier
        metadata = self.owned(service)
        require(not metadata["HostConfig"].get("Binds")
                and all(mount["Type"] == "tmpfs" for mount in metadata["Mounts"]),
                "Refusing persistent or bind mounts.")
        docker("container", "start", identifier)

    def guard(self):
        """Check the live test target and all container attachments."""
        containers = {service: self.owned(service) for service in self.containers}
        network = json.loads(docker("network", "inspect", self.network_id))[0]
        return validate_target(self.base_url, self.run_id, containers, network)

    def statistics_control(self, action):
        """Start or stop only this run's Statistics container."""
        require(action in {"start", "stop"}, "Unexpected lifecycle action.")
        self.owned("statistics")
        docker("container", action, self.containers["statistics"])

    def prepare(self):
        """Prepare a separate tmpfs database and the two application containers."""
        # Use local ARM64 images only; do not build or download images here.
        for image in (self.arguments.tasks_image, self.arguments.statistics_image, self.arguments.postgres_image):
            metadata = json.loads(docker("image", "inspect", image))[0]
            require(metadata["Os"] == "linux" and metadata["Architecture"] == "arm64",
                    "Only existing Linux ARM64 images are accepted; no pulls are performed.")
            if image != self.arguments.postgres_image:
                require(metadata["Config"]["User"] == "10001:10001", "Application image must be non-root.")
        self.network_id = docker("network", "create", "--driver", "bridge", "--label", f"{LABEL}={self.run_id}", self.network)
        # These passwords belong only to the temporary test database.
        administrator_password = secrets.token_hex(32)
        application_password = secrets.token_hex(32)
        self.create("postgres", self.arguments.postgres_image, {
            "POSTGRES_DB": "pa2577", "POSTGRES_PASSWORD": administrator_password,
            "POSTGRES_HOST_AUTH_METHOD": "scram-sha-256",
            "POSTGRES_INITDB_ARGS": "--auth-host=scram-sha-256 --auth-local=scram-sha-256",
        }, "--memory", "512m", "--tmpfs", "/var/lib/postgresql/data:rw,nosuid,size=256m")
        deadline = time.monotonic() + 60
        while True:
            result = subprocess.run(
                ["docker", "exec", self.containers["postgres"], "pg_isready", "-h", "127.0.0.1", "-U", "postgres", "-d", "pa2577"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                break
            require(time.monotonic() < deadline, "Temporary PostgreSQL readiness timed out.")
        # Only the new database gets this schema and limited application role.
        statement = (
            "BEGIN; CREATE ROLE pa2577_tasks LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            f"NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD '{application_password}'; "
            "REVOKE CREATE, TEMPORARY ON DATABASE pa2577 FROM PUBLIC; "
            "REVOKE CREATE ON SCHEMA public FROM PUBLIC; "
            "GRANT CONNECT ON DATABASE pa2577 TO pa2577_tasks; "
            "CREATE SCHEMA tasks AUTHORIZATION postgres; REVOKE ALL ON SCHEMA tasks FROM PUBLIC; "
            "CREATE TABLE tasks.tasks (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
            "title varchar(200) NOT NULL CHECK (char_length(btrim(title)) > 0), "
            "completed boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP); "
            "GRANT USAGE ON SCHEMA tasks TO pa2577_tasks; "
            "GRANT SELECT, DELETE ON tasks.tasks TO pa2577_tasks; "
            "GRANT INSERT (title, completed), UPDATE (title, completed) ON tasks.tasks TO pa2577_tasks; "
            "GRANT USAGE ON SEQUENCE tasks.tasks_id_seq TO pa2577_tasks; COMMIT;"
        )
        self.owned("postgres")
        docker("exec", "--interactive", self.containers["postgres"], "sh", "-c",
               'export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -X --quiet --no-password '
               '-h 127.0.0.1 -U postgres -d pa2577 -v ON_ERROR_STOP=1', input_text=statement)
        runtime = ("--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "--cap-drop", "ALL", "--memory", "256m")
        self.create("statistics", self.arguments.statistics_image, {
            "TASKS_API_URL": "http://tasks:8000", "TASKS_TIMEOUT_SECONDS": "2",
        }, *runtime)
        self.create("tasks", self.arguments.tasks_image, {
            "DB_HOST": "db", "DB_PORT": "5432", "DB_NAME": "pa2577", "DB_USER": "pa2577_tasks",
            "DB_PASSWORD": application_password, "STATISTICS_API_URL": "http://statistics:8000",
            "STATISTICS_TIMEOUT_SECONDS": "3",
        }, *runtime, "--publish", "127.0.0.1::8000")
        ports = self.owned("tasks")["NetworkSettings"]["Ports"]
        self.base_url = self.arguments.base_url or "http://127.0.0.1:" + ports["8000/tcp"][0]["HostPort"]
        # Validate isolation before sending the first HTTP request.
        self.base_url = self.guard()
        deadline = time.monotonic() + 30
        probe = IsolatedHTTPTests(methodName="test_create_list_statistics_complete_delete")
        probe.base_url = self.base_url
        probe.created_ids = set()
        while True:
            try:
                ready = probe.http("GET", "/ready") == (200, {"status": "ok"})
                statistics = probe.http("GET", "/api/statistics")
                if ready and statistics == (200, {"total": 0, "completed": 0, "pending": 0}):
                    break
            except OSError:
                pass
            require(time.monotonic() < deadline, "Temporary HTTP services did not become ready.")
        print("Isolated target:", self.base_url, flush=True)

    def cleanup(self):
        """Remove only recorded resources whose ownership still matches."""
        failures = []
        for service in reversed(self.containers):
            try:
                self.owned(service)
                docker("container", "rm", "--force", self.containers[service])
            except (RuntimeError, ValueError, subprocess.SubprocessError):
                failures.append(service)
        if self.network_id is not None:
            try:
                network = json.loads(docker("network", "inspect", self.network_id))[0]
                require(network["Labels"].get(LABEL) == self.run_id, "Refusing unowned network.")
                docker("network", "rm", self.network_id)
            except (RuntimeError, ValueError, subprocess.SubprocessError):
                failures.append("network")
        if failures:
            raise RuntimeError("Cleanup incomplete for own resources: " + ", ".join(failures))
        print("Only this run's containers/network removed; temporary tmpfs data discarded.", flush=True)


def main(argv=None):
    """Print the plan by default or run tests after explicit approval."""
    parser = argparse.ArgumentParser(description="Plan isolated HTTP integration; execution requires --execute.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--tasks-image", default="pa2577-tasks:todo5-smoke")
    parser.add_argument("--statistics-image", default="pa2577-statistics:todo5-smoke")
    parser.add_argument("--postgres-image", default="docker.io/library/postgres:17-bookworm")
    parser.add_argument("--base-url", help="Optional target override; must match this run's inspected loopback binding.")
    arguments = parser.parse_args(argv)
    if not arguments.execute:
        print("PLAN ONLY: no Docker calls, containers, network, HTTP requests, or secret generation.")
        print("Images:", arguments.tasks_image, arguments.statistics_image, arguments.postgres_image)
        print("Resources: unique labeled network + Tasks + Statistics + PostgreSQL; PostgreSQL data on 256 MiB tmpfs.")
        print("Only Tasks published: 127.0.0.1:<Docker-assigned-port>:8000. No volumes, bind mounts, Compose, or pulls.")
        print("The internal database is named pa2577 because the existing Tasks image requires it; server/data are isolated.")
        print("Await approval before passing --execute.")
        return 0
    run = IsolatedRun(arguments)
    try:
        run.prepare()
        IsolatedHTTPTests.base_url = run.base_url
        IsolatedHTTPTests.run_id = run.run_id
        IsolatedHTTPTests.target_guard = staticmethod(run.guard)
        IsolatedHTTPTests.statistics_control = staticmethod(run.statistics_control)
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(IsolatedHTTPTests)
        )
        return 0 if result.wasSuccessful() else 1
    finally:
        # Try cleanup even when setup or a test fails.
        run.cleanup()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)