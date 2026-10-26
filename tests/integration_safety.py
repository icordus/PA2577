"""Reject integration targets that could reach native application data."""

from urllib.parse import urlsplit


LABEL = "pa2577.integration.run"
FORBIDDEN_PORTS = {5000, 5001, 5432, 55432}


def require(condition, message):
    """Stop validation when a safety condition is not met."""
    if not condition:
        raise ValueError(message)


def validate_target(base_url, run_id, containers, network):
    """Check the target URL, resource ownership, storage, and service settings."""
    parsed = urlsplit(base_url)
    # Native ports and remote addresses must never be test targets.
    require(
        parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
        and parsed.username is None and parsed.password is None
        and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment
        and parsed.port is not None and parsed.port not in FORBIDDEN_PORTS,
        "Refusing native, remote, or malformed HTTP target.",
    )
    require(len(run_id) == 32 and all(character in "0123456789abcdef" for character in run_id),
            "A unique test run identifier is required.")
    require(network["Labels"].get(LABEL) == run_id, "Network is not owned by this run.")
    require(set(containers) == {"tasks", "statistics", "postgres"}, "Three isolated services are required.")
    require(set(network.get("Containers", {})) == {container["Id"] for container in containers.values()},
            "Network must contain only this run's three services.")
    # Each container must belong only to this run and use temporary storage.
    for service, container in containers.items():
        require(container["Config"]["Labels"].get(LABEL) == run_id,
                "Container is not owned by this run.")
        require(container["Name"] == f"/pa2577-it-{run_id}-{service}", "Unexpected container name.")
        require(container["State"]["Running"], "Test container is not running.")
        networks = container["NetworkSettings"]["Networks"]
        require(len(networks) == 1 and next(iter(networks.values()))["NetworkID"] == network["Id"],
                "Test container has an unexpected network attachment.")
        require(not container["HostConfig"].get("Binds"), "Host bind mounts are forbidden.")
        require(all(mount["Type"] == "tmpfs" for mount in container["Mounts"]),
                "Persistent or host data mounts are forbidden.")
        if service != "tasks":
            require(not any(container["HostConfig"].get("PortBindings", {}).values()),
                    "Only Tasks may publish a port.")
            require(not any(container["NetworkSettings"]["Ports"].values()),
                    "Internal service has a published port.")
    # The URL must match the actual loopback port published by Tasks.
    bindings = containers["tasks"]["NetworkSettings"]["Ports"]
    require(bindings == {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(parsed.port)}]},
            "HTTP target does not match the isolated Tasks publication.")
    postgres = containers["postgres"]
    require("/var/lib/postgresql/data" in postgres["HostConfig"].get("Tmpfs", {}),
            "Test PostgreSQL data must be on tmpfs.")
    # Use internal test aliases, never the native database hostname.
    tasks_environment = dict(
                entry.split("=", 1) for entry in containers["tasks"]["Config"]["Env"]
        )
    require(tasks_environment.get("DB_HOST") == "db" and tasks_environment.get("DB_PORT") == "5432"
            and tasks_environment.get("DB_NAME") == "pa2577"
            and tasks_environment.get("DB_USER") == "pa2577_tasks"
            and tasks_environment.get("STATISTICS_API_URL") == "http://statistics:8000",
            "Tasks must use this run's database and Statistics aliases.")
    stats_environment = dict(entry.split("=", 1) for entry in containers["statistics"]["Config"]["Env"])
    require(stats_environment.get("TASKS_API_URL") == "http://tasks:8000"
            and not any(key.startswith(("DB_", "PG")) or key == "DATABASE_URL"
                        for key in stats_environment), "Statistics must not receive database credentials.")
    return base_url.rstrip("/")