"""Check integration safety with fake metadata and no running containers."""

import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from integration_safety import LABEL, validate_target


class IntegrationSafetyTests(unittest.TestCase):
    """Check which targets and container settings the runner may use."""

    def setUp(self):
        """Build fake metadata for one valid isolated test run."""
        # These dictionaries do not create any Docker resources.
        self.run_id = "a" * 32
        self.network = {"Id": "isolated-network-id", "Labels": {LABEL: self.run_id}}
        self.containers = {}
        for service in ("tasks", "statistics", "postgres"):
            self.containers[service] = {
                "Id": "test-" + service,
                "Name": f"/pa2577-it-{self.run_id}-{service}",
                "Config": {"Labels": {LABEL: self.run_id}, "Env": []},
                "State": {"Running": True},
                "HostConfig": {"PortBindings": {}, "Tmpfs": {}},
                "Mounts": [],
                "NetworkSettings": {"Networks": {"test": {"NetworkID": self.network["Id"]}}, "Ports": {}},
            }
            self.network["Containers"] = {container["Id"]: {} for container in self.containers.values()}
        self.containers["tasks"]["NetworkSettings"]["Ports"] = {
            "8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "32768"}]
        }
        self.containers["tasks"]["Config"]["Env"] = [
            "DB_HOST=db", "DB_PORT=5432", "DB_NAME=pa2577", "DB_USER=pa2577_tasks",
            "STATISTICS_API_URL=http://statistics:8000",
        ]
        self.containers["statistics"]["Config"]["Env"] = ["TASKS_API_URL=http://tasks:8000"]
        self.containers["postgres"]["HostConfig"]["Tmpfs"] = {"/var/lib/postgresql/data": "rw,size=256m"}

    def validate(self, url="http://127.0.0.1:32768"):
        """Check a URL against the fake containers and network."""
        return validate_target(url, self.run_id, self.containers, self.network)

    def test_accepts_only_owned_isolated_target(self):
        """Accept the loopback port published by this test run."""
        self.assertEqual(self.validate(), "http://127.0.0.1:32768")

    def test_rejects_native_remote_and_redirect_targets(self):
        """Reject native ports, remote hosts, and unexpected URL parts."""
        for url in ("http://127.0.0.1:5000", "http://127.0.0.1:5001", "http://127.0.0.1:55432",
                    "http://127.0.0.1:5432", "http://localhost:32768", "http://192.168.0.71:32768",
                    "http://127.0.0.1:32769", "http://127.0.0.1:32768/api/tasks",
                    "http://user:password@127.0.0.1:32768", "http://127.0.0.1:32768?target=real"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.validate(url)

    def test_rejects_wrong_ownership_and_network(self):
        """Reject another run's network or an extra network connection."""
        self.network["Labels"][LABEL] = "another-run"
        with self.assertRaises(ValueError):
            self.validate()
        self.network["Labels"][LABEL] = self.run_id
        self.containers["tasks"]["NetworkSettings"]["Networks"]["real"] = {"NetworkID": "real"}
        with self.assertRaises(ValueError):
            self.validate()

    def test_rejects_real_database_and_persistent_mounts(self):
        """Reject stored data mounts and the native database hostname."""
        original = copy.deepcopy(self.containers)
        for mount_type in ("volume", "bind"):
            self.containers = copy.deepcopy(original)
            self.containers["postgres"]["Mounts"] = [{"Type": mount_type}]
            with self.assertRaises(ValueError):
                self.validate()
        self.containers = original
        self.containers["tasks"]["Config"]["Env"][0] = "DB_HOST=pa2577-postgres"
        with self.assertRaises(ValueError):
            self.validate()

    def test_rejects_published_internal_services_and_statistics_credentials(self):
        """Keep PostgreSQL internal and database settings out of Statistics."""
        self.containers["postgres"]["HostConfig"]["PortBindings"] = {"5432/tcp": [{}]}
        with self.assertRaises(ValueError):
            self.validate()
        self.containers["postgres"]["HostConfig"]["PortBindings"] = {}
        self.containers["statistics"]["Config"]["Env"].append("DB_PASSWORD=placeholder")
        with self.assertRaises(ValueError):
            self.validate()

    def test_rejects_additional_network_members_and_missing_tmpfs(self):
        """Reject extra containers or a database without temporary storage."""
        self.network["Containers"]["existing-postgres"] = {}
        with self.assertRaises(ValueError):
            self.validate()
        self.network["Containers"].pop("existing-postgres")
        self.containers["postgres"]["HostConfig"]["Tmpfs"] = {}
        with self.assertRaises(ValueError):
            self.validate()


class RunnerSafetyTests(unittest.TestCase):
    """Check planning and cleanup without making real Docker calls."""

    @classmethod
    def setUpClass(cls):
        """Import the runner without executing its main command."""
        script = Path(__file__).resolve().parents[1] / "scripts" / "integration_http.py"
        specification = importlib.util.spec_from_file_location("integration_runner_safety", script)
        cls.runner = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.runner)

    def test_default_plan_cannot_invoke_docker_or_generate_credentials(self):
        """Check that the default command only prints a plan."""
        # Mocks record calls without creating resources or passwords.
        with patch.object(self.runner, "docker") as docker, \
             patch.object(self.runner.secrets, "token_hex") as generate, patch("sys.stdout"):
            self.assertEqual(self.runner.main([]), 0)
        docker.assert_not_called()
        generate.assert_not_called()

    def test_explicit_run_id_is_used_without_docker_calls(self):
        """Use the job ID so fallback cleanup can find only its resources."""
        with patch.object(self.runner, "docker") as docker:
            run = self.runner.IsolatedRun(SimpleNamespace(run_id="b" * 32))
        self.assertEqual(run.run_id, "b" * 32)
        self.assertEqual(run.network, "pa2577-it-" + "b" * 32)
        docker.assert_not_called()

    def test_invalid_run_id_is_rejected_before_resource_creation(self):
        """Reject IDs that could select another resource name."""
        for run_id in ("pa2577-postgres", "../native", "A" * 32, "c" * 31):
            with self.subTest(run_id=run_id), self.assertRaises(ValueError):
                self.runner.IsolatedRun(SimpleNamespace(run_id=run_id))

    def test_cleanup_refuses_container_with_wrong_run_label(self):
        """Refuse to remove a container labeled for another run."""
        run = self.runner.IsolatedRun(None)
        run.containers = {"tasks": "test-owned-id"}
        container = {"Id": "test-owned-id", "Name": f"/{run.network}-tasks",
                     "Config": {"Labels": {LABEL: "different-run"}}}
        with patch.object(self.runner, "inspect_container", return_value=container), \
             patch.object(self.runner, "docker") as docker:
            with self.assertRaisesRegex(RuntimeError, "Cleanup incomplete"):
                run.cleanup()
        docker.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)