"""Check integration safety with fake metadata and no running containers."""

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
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


class CICleanupSafetyTests(unittest.TestCase):
    """Check extracted CI helpers without accessing a Docker daemon."""

    @classmethod
    def setUpClass(cls):
        """Import the CI scripts without running their entry points."""
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        for name in ("ci_cleanup", "ci_run_id"):
            specification = importlib.util.spec_from_file_location(name, scripts / (name + ".py"))
            module = importlib.util.module_from_spec(specification)
            specification.loader.exec_module(module)
            setattr(cls, name, module)

    def setUp(self):
        """Provide fake job settings and block all subprocess execution."""
        self.run_id = "a" * 32
        self.environment = {
            "INTEGRATION_RUN_ID": self.run_id,
            "TASKS_BUILD_IMAGE": "test-tasks:sha",
            "STATISTICS_BUILD_IMAGE": "test-statistics:sha",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        environment = patch.dict(self.ci_cleanup.os.environ, self.environment, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        subprocess = patch.object(self.ci_cleanup.subprocess, "run", return_value=SimpleNamespace(returncode=1))
        self.process = subprocess.start()
        self.addCleanup(subprocess.stop)
        output = patch("sys.stdout")
        output.start()
        self.addCleanup(output.stop)

    def test_invalid_run_id_prevents_docker_access(self):
        """Reject invalid ownership IDs before listing or removing anything."""
        with patch.dict(self.ci_cleanup.os.environ, {"INTEGRATION_RUN_ID": "../other"}), \
             patch.object(self.ci_cleanup, "docker") as docker:
            with self.assertRaisesRegex(RuntimeError, "Invalid run ID"):
                self.ci_cleanup.main()
        docker.assert_not_called()
        self.process.assert_not_called()

    def test_owned_container_and_empty_network_are_removed(self):
        """Remove only resources whose names and labels match this run."""
        prefix = "pa2577-it-" + self.run_id
        container = {"Id": "owned-container", "Name": "/" + prefix + "-tasks",
                     "Config": {"Labels": {LABEL: self.run_id}}}
        network = {"Id": "owned-network", "Name": prefix,
                   "Labels": {LABEL: self.run_id}, "Containers": {}}
        responses = ["owned-container", json.dumps([container]), "",
                     "owned-network", json.dumps([network]), ""]
        with patch.object(self.ci_cleanup, "docker", side_effect=responses) as docker:
            self.ci_cleanup.main()
        self.assertIn(unittest.mock.call("container", "rm", "--force", "owned-container"), docker.call_args_list)
        self.assertIn(unittest.mock.call("network", "rm", "owned-network"), docker.call_args_list)

    def test_foreign_container_and_busy_network_are_preserved(self):
        """Report mismatched ownership or active members without removing them."""
        prefix = "pa2577-it-" + self.run_id
        container = {"Id": "foreign", "Name": "/" + prefix + "-tasks",
                     "Config": {"Labels": {LABEL: "another-run"}}}
        network = {"Id": "busy", "Name": prefix, "Labels": {LABEL: self.run_id},
                   "Containers": {"remaining-container": {}}}
        responses = ["foreign", json.dumps([container]), "busy", json.dumps([network])]
        with patch.object(self.ci_cleanup, "docker", side_effect=responses) as docker:
            with self.assertRaisesRegex(SystemExit, "Cleanup incomplete"):
                self.ci_cleanup.main()
        self.assertFalse(any("rm" in call.args for call in docker.call_args_list))

    def test_credentials_are_cleaned_when_docker_fails(self):
        """Remove only the job credential directory even after Docker fails."""
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "pa2577-docker-123-1-test"
            config.mkdir()
            with patch.dict(self.ci_cleanup.os.environ, {"RUNNER_TEMP": temporary, "DOCKER_CONFIG": str(config)}), \
                 patch.object(self.ci_cleanup, "docker", side_effect=RuntimeError("Docker unavailable")), \
                 patch.object(self.ci_cleanup.shutil, "rmtree") as remove:
                with self.assertRaisesRegex(RuntimeError, "Docker unavailable"):
                    self.ci_cleanup.main()
                remove.assert_called_once_with(config)

    def test_unexpected_credential_path_is_preserved(self):
        """Refuse directories outside the expected job-specific name."""
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "unrelated"
            config.mkdir()
            settings = {"INTEGRATION_RUN_ID": "", "RUNNER_TEMP": temporary, "DOCKER_CONFIG": str(config)}
            with patch.dict(self.ci_cleanup.os.environ, settings), \
                 patch.object(self.ci_cleanup.shutil, "rmtree") as remove:
                with self.assertRaisesRegex(RuntimeError, "unexpected Docker configuration path"):
                    self.ci_cleanup.main()
                remove.assert_not_called()

    def test_run_id_is_written_to_github_environment(self):
        """Append a unique run ID without replacing earlier environment entries."""
        with tempfile.TemporaryDirectory() as temporary:
            environment = Path(temporary) / "environment"
            environment.write_text("EXISTING=value\n")
            with patch.dict(self.ci_run_id.os.environ, {"GITHUB_ENV": str(environment)}):
                self.ci_run_id.main()
            self.assertRegex(environment.read_text(), r"^EXISTING=value\nINTEGRATION_RUN_ID=[0-9a-f]{32}\n$")
        self.process.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)