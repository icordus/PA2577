"""Remove only temporary Docker resources owned by the current CI job."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def docker(*arguments):
    """Run a Docker cleanup command and reject unsuccessful results."""
    result = subprocess.run(["docker", *arguments], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Docker cleanup failed; no broad deletion attempted.")
    return result.stdout.strip()


def main():
    """Check resource ownership before cleanup, including on earlier failures."""
    failures = []
    try:
        run_id = os.environ.get("INTEGRATION_RUN_ID", "")
        if run_id:
            if not re.fullmatch(r"[0-9a-f]{32}", run_id):
                raise RuntimeError("Invalid run ID; refusing cleanup.")
            label = "pa2577.integration.run=" + run_id
            prefix = "pa2577-it-" + run_id
            # Names and labels must both match this run before removal.
            containers = docker("container", "ls", "--all", "--quiet", "--filter", "label=" + label).split()
            for identifier in containers:
                try:
                    data = json.loads(docker("container", "inspect", identifier))[0]
                    expected_names = {"/" + prefix + "-" + service for service in ("tasks", "statistics", "postgres")}
                    if data["Name"] not in expected_names or data["Config"]["Labels"].get("pa2577.integration.run") != run_id:
                        raise RuntimeError("Container ownership mismatch; refusing removal.")
                    docker("container", "rm", "--force", data["Id"])
                except (RuntimeError, ValueError, KeyError):
                    failures.append("container")
            networks = docker("network", "ls", "--quiet", "--filter", "label=" + label).split()
            for identifier in networks:
                try:
                    data = json.loads(docker("network", "inspect", identifier))[0]
                    if data["Name"] != prefix or data["Labels"].get("pa2577.integration.run") != run_id or data.get("Containers"):
                        raise RuntimeError("Network ownership mismatch or remaining members.")
                    docker("network", "rm", data["Id"])
                except (RuntimeError, ValueError, KeyError):
                    failures.append("network")
        for variable in ("TASKS_BUILD_IMAGE", "STATISTICS_BUILD_IMAGE"):
            image = os.environ[variable]
            result = subprocess.run(["docker", "image", "inspect", image], capture_output=True)
            if result.returncode == 0:
                try:
                    docker("image", "rm", image)
                except RuntimeError:
                    failures.append("local build tag")
    finally:
        # Delete credentials even if Docker cleanup fails, but only at the job path.
        docker_config = os.environ.get("DOCKER_CONFIG")
        if docker_config:
            runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
            config = Path(docker_config)
            expected_prefix = (
                "pa2577-docker-" + os.environ["GITHUB_RUN_ID"] + "-"
                + os.environ["GITHUB_RUN_ATTEMPT"] + "-"
            )
            if (config.is_symlink() or config.parent.resolve() != runner_temp
                    or not config.name.startswith(expected_prefix)):
                raise RuntimeError("Refusing an unexpected Docker configuration path.")
            if config.exists():
                shutil.rmtree(config)
    if failures:
        raise SystemExit("Cleanup incomplete: " + ", ".join(failures))
    print("Job-scoped cleanup complete. No volumes or unrelated resources were removed.")


if __name__ == "__main__":
    main()