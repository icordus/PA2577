"""Prepare the Tasks role and schema once in the existing project database."""

import os
from pathlib import Path
import secrets
import subprocess

from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]


def execute_admin(statement):
    """Send SQL through stdin and keep database errors out of the output."""
    result = subprocess.run(
        [
            "docker", "exec", "--interactive", "pa2577-postgres", "sh", "-c",
            'export PGPASSWORD="$(cat /run/secrets/postgres-password)"; '
            'exec psql -X --quiet --no-password -h 127.0.0.1 -U postgres '
            '-d pa2577 -v ON_ERROR_STOP=1 --tuples-only --no-align',
        ],
        input=statement,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise SystemExit("Database preparation failed; output suppressed to protect credentials.")
    return result.stdout.strip()


def main():
    """Create the limited role, task table, and protected local settings."""
    environment = ROOT / ".env"
    # Refuse to overwrite existing settings or database objects.
    if environment.exists() or environment.is_symlink():
        raise SystemExit("Stop: .env already exists; no changes made.")
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", ".env"], cwd=ROOT, check=False
    )
    if ignored.returncode:
        raise SystemExit("Stop: .env must be ignored by Git.")
    conflicts = execute_admin(
        "SELECT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pa2577_tasks') "
        "OR EXISTS (SELECT FROM pg_namespace WHERE nspname = 'tasks');"
    )
    if conflicts != "f":
        raise SystemExit("Stop: Tasks role or schema already exists; no resources reused.")
    # Create the password locally without printing it or replacing a file.
    password = secrets.token_hex(32)
    descriptor = os.open(
        environment, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as target:
        target.write(
            "DB_HOST=127.0.0.1\nDB_PORT=55432\nDB_NAME=pa2577\n"
            f"DB_USER=pa2577_tasks\nDB_PASSWORD={password}\n"
        )
    role_statement = sql.SQL(
        "CREATE ROLE pa2577_tasks LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
        "NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 10 PASSWORD {};"
    ).format(sql.Literal(password)).as_string()
    # Keep ownership with the administrator and grant only task access.
    execute_admin(
        "BEGIN;\n" + role_statement + "\n"
        "REVOKE CREATE, TEMPORARY ON DATABASE pa2577 FROM PUBLIC;\n"
        "REVOKE CREATE ON SCHEMA public FROM PUBLIC;\n"
        "GRANT CONNECT ON DATABASE pa2577 TO pa2577_tasks;\n"
        "CREATE SCHEMA tasks AUTHORIZATION postgres;\n"
        "REVOKE ALL ON SCHEMA tasks FROM PUBLIC;\n"
        "CREATE TABLE tasks.tasks ("
        "id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
        "title varchar(200) NOT NULL CHECK (char_length(btrim(title)) > 0), "
        "completed boolean NOT NULL DEFAULT false, "
        "created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP);\n"
        "GRANT USAGE ON SCHEMA tasks TO pa2577_tasks;\n"
        "GRANT SELECT, DELETE ON tasks.tasks TO pa2577_tasks;\n"
        "GRANT INSERT (title, completed), UPDATE (title, completed) "
        "ON tasks.tasks TO pa2577_tasks;\n"
        "GRANT USAGE ON SEQUENCE tasks.tasks_id_seq TO pa2577_tasks;\n"
        "COMMIT;\n"
    )
    print("Tasks role and schema created; protected .env generated without displaying secrets.")


if __name__ == "__main__":
    main()