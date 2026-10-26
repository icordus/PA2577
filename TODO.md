# PA2577 Task Manager Progress

Implement one stage at a time. Stop after each stage, explain the changes,
provide verification commands and expected results, and wait for the user's
results before continuing. Check items only after their verification succeeds.

## Working Rules

- Keep the previous project unchanged. Do not commit, push, or deploy automatically.
- Do not upgrade or reinstall Kubernetes, run sudo automatically, or delete
  existing volumes, data, or cluster resources.
- Explain infrastructure installations and wait for confirmation first.
- Never commit credentials, .env files, or kubeconfig.
- Keep responsibilities clear and components minimal. Report verification gaps.
- Do not create or use Docker Compose. Build images with Docker; Kubernetes
  orchestration and full integration are reserved for TODO 8/9, with approval
  before deployment. TODO 5 smoke checks must not use the existing database.

## TODO 0 - Inspect Projects and Environment (Closed; Deferred Items Recorded)

- [x] Inspect PA2577 and the previous project, including available instructions.
- [x] Verify the previous project's actual folder and Git remote: PA2595.
- [x] Locate existing workflows, configured runner labels, Dockerfile, and Helm configuration.
- [x] Determine the current terminal host and inspect its listening TCP ports.
- [x] Document reusable patterns and incompatible deployment practices below.
- [x] Create this staged progress checklist.
- [x] Verify Pi Linux ARM64/64-bit, Python version, and Docker client/Compose versions (remote report).
- [x] Verify a working Python virtual environment with pip in /home/ico/git/PA2577/.venv.
- [ ] TODO 5: finish isolated image validation; full Kubernetes integration is deferred to TODO 8/9. No Docker Compose.
- [x] Verify Kubernetes connectivity, node readiness, workloads, and occupied Pi ports (remote report).
- [x] Confirm PA2577 runner availability: the user reports GitHub says "There are no runners configured".
- [ ] TODO 7: configure or grant an appropriate runner, verify labels/status/access, and execute a real PA2577 job.
- [x] Review the user's remote inspection report; record successes and unresolved findings.
- [x] Close inspection with container tooling and runner prerequisites explicitly deferred.

### Current Pi Follow-Up (2026-10-25)

This section supersedes the historical Mac notes and initial Pi failures below.

- The user corrected the container runtime to Docker after initially reporting
  Podman. Podman was not found during read-only inspection. A subsequent Docker
  check succeeded without sudo: client/server 24.0.6, Linux ARM64/aarch64,
  Compose v2.21.0. No Docker installation, group, or socket changes were made.
  The earlier permission failure is historical, not the current access state.
  Compose was later explicitly excluded by the user. Full integration is
  reserved for Kubernetes in TODO 8/9; TODO 5 covers only images and smoke tests.
- GitHub PA2577 reports no configured runners, as confirmed by the user.
  Existing PA2595/PA2579 registrations do not provide PA2577 access. This does not
  block local Flask development; runner preparation remains for TODO 7.
- After approval, the user installed python3.10-venv and its pip/setuptools wheel
  dependencies. The existing .venv was verified with Python 3.10.12, pip 22.0.2,
  an isolated interpreter/pip path, and a successful pip check.
- TODO 1 uses only this virtual environment. No containers, database, sudo,
  Kubernetes changes, commits, pushes, or deployments were used for TODO 1.

### Verified Local Findings (Mac Inspection)

- PA2577 initially contained only README.md (`# PA2577`). Its working tree was clean.
  Origin: https://github.com/icordus/PA2577.git.
- Previous project: /Users/iulian/git/PA2595, with origin
  git@github.com:icordus/PA2595.git. Its working tree was clean during inspection.
  No PA2579 folder was present in /Users/iulian/git.
- No AGENTS.md, copilot-instructions.md, or scoped instruction files were found
  in either project. No ancestor AGENTS.md was found up to the filesystem root.
- This terminal runs on the Mac: Darwin 22.6.0, x86_64. This does not describe the Pi.
- Mac listening TCP ports observed: 51337, 59687, 59787, 52759, 52885.
  No listeners were observed on 5000, 5001, 5432, 8000, or 30080 at inspection time.
  Listener visibility is limited to what the current account can inspect.
- PA2595 workflows: .github/workflows/ci.yml and release.yml use the configured
  label `raspberrypi2`; deploy-test-api.yml uses `[self-hosted, linux, ARM64]`.
  These are configuration facts, not proof of available or healthy runners.
- PA2595's Dockerfile uses python:3.11-slim and Uvicorn on container port 8000.
  No Compose definition was found in either project.
- PA2595's Helm chart is helm/student-risk-api. Its service defaults to
  ClusterIP port 80 -> 8000; the deployment workflow selects NodePort 30080
  at the configured address 192.168.0.71. Actual Pi port usage is unverified.
- Reuse the ideas behind health endpoints, HTTP regression checks, Helm probes,
  and CPU/memory budgets. Do not copy ML dependencies, FastAPI/Uvicorn startup,
  hard-coded image tags, or deployment steps that use sudo/containerd imports
  and imagePullPolicy=Never. PA2577 will use Flask, Gunicorn in containers,
  Docker Hub images, and separate CI/deployment workflows.
- Plain Kubernetes manifests should be sufficient for this small project;
  Helm is an available reference, not a required new component.
- During Mac inspection, kubectl v1.28.5 / server v1.28.15 were not reverified;
  they were subsequently confirmed in the remote report below.
  Kubernetes 1.28 is out of upstream support; do not upgrade it as part of this
  project. Later manifests must use APIs supported by the existing cluster.

### Raspberry Pi Results Reported by the Remote Agent (2026-10-25)

These results come from the user's pasted remote-agent report, not commands
executed from this Mac session. They describe the time of that inspection.

- Host raspberrypi2: Raspberry Pi 4 Model B Rev 1.5, approximately 8 GB RAM,
  Ubuntu 22.04.3 LTS, kernel 5.15.0-1105-raspi, aarch64, 64-bit userspace.
- PA2577 is at /home/ico/git/PA2577 with the expected HTTPS origin. A local,
  untracked TODO.md exists there; its identity with this Mac copy is unverified.
- /home/ico/git/PA2595 has origin https://github.com/icordus/PA2595.git and
  branch feature/update_app. All three workflows there use raspberrypi2.
  This differs from the Mac checkout; do not overwrite either project to reconcile it.
- Python 3.10.12: venv imports, but pip and ensurepip are missing. A working
  virtual environment has not been demonstrated. No packages were installed.
- Docker client 24.0.6 linux/arm64 and Compose v2.21.0 are available. Docker
  service is active, but ico cannot access the root:docker socket and is not
  in the docker group. Server version and published container ports are unverified.
  Docker-group membership grants effectively root-level access; any permission
  change requires a separate decision, not an automatic fix.
- Kubernetes context kubernetes-admin@kubernetes reaches server v1.28.15;
  client and kubelet are v1.28.5. Node raspberrypi2 (192.168.0.71) is Ready.
  All 11 observed pods were Running and 1/1 ready; containerd is 1.6.24.
- NodePorts 30080 (student-risk-api) and 31674 (nginx) are allocated. No TCP
  listeners were observed on 5000, 5001, 5432, or 8000; this is not a reservation.
- No pa2577 namespace, StorageClass, PV, or PVC was reported. Helm is v3.20.2.
  Storage preparation remains for TODO 8, with explanation and approval first.
- calico-system is Terminating; scheduler/controller-manager had recent restarts.
  Full cluster health, application connectivity, and runner cluster access were
  not demonstrated. Do not repair or remove existing cluster resources here.
- Two local runner services are active, registered to PA2595 and PA2579,
  with version 2.338.0 in logs. PA2579 is therefore a separate runner registration,
  not evidence that the inspected previous application repository is PA2579.
  GitHub online status, actual labels, and PA2577 access remain unverified.
- The remote agent reported no project modifications, sudo, installations,
  commits, pushes, or deployments. This Mac update does not update the Pi copy.

### Read-Only Diagnostic Reference and Remaining GitHub Checks

The Pi command block below is retained for reproducibility, not a request to
repeat all completed diagnostics. Known Python and Docker failures above need
an agreed prerequisite step; do not attempt repairs automatically.

Run these in a terminal connected to the Pi, not in the current Mac terminal.
Run the Kubernetes commands with the account/context intended for the project.
Do not install anything or change permissions if a command fails; share the error.
Do not share tokens, passwords, .env contents, or kubeconfig.

```bash
hostname
uname -srm
getconf LONG_BIT
python3 --version
python3 -m pip --version
python3 -m venv --help >/dev/null && printf 'venv module available\n'
docker version
docker info --format 'OS={{.OSType}} Architecture={{.Architecture}}'
docker compose version
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
ss -ltn
kubectl config current-context
kubectl version --output=yaml --request-timeout=10s
kubectl get nodes -o wide --request-timeout=10s
kubectl get pods -A -o wide --request-timeout=10s
kubectl get services -A -o wide --request-timeout=10s
```

Expected evidence: Linux aarch64/arm64 and 64 bits; Python, pip, and venv
availability; Docker client AND server reachable without sudo; Docker reporting
linux/arm64 or equivalent; Compose v2; current listening/published ports;
the intended Kubernetes context, actual client/server versions, Ready nodes,
and workload/service status. Missing tools or permissions are findings, not a
reason to install or reconfigure automatically. `venv --help` checks the module,
not whether creating a working environment will succeed; verify that in TODO 1.
`ss` alone cannot exclude Kubernetes NodePort allocations, so also inspect Services.

In GitHub, inspect Settings -> Actions -> Runners for both icordus/PA2595 and
icordus/PA2577. Share only runner names, labels, status, version if displayed,
and repository/organization scope or runner-group access. If a field is not
visible, report that instead of guessing. An idle/online runner is not proof a
PA2577 job can execute; verify a real job in TODO 7. A runner registered only to
PA2595 is not automatically available to PA2577: it needs a separate repository
registration in a separate runner directory, or an organization runner with
access granted to PA2577. Do not reconfigure the existing runner during this stage.

## TODO 1 - First Flask Service (Verified)

- [x] Create services/tasks/app.py with GET /health returning {"status": "ok"}.
- [x] Run locally on 127.0.0.1:5000 with debug disabled; no containers or database.
- [x] Add requirements.txt and .gitignore; explain Python virtual environments below.
- [x] Verify the running service with curl: HTTP 200, application/json, exactly {"status": "ok"}.
- [x] User independently verified /health: HTTP 200 and {"status":"ok"} (2026-10-25).

The .venv directory isolates this project's Python packages from system Python.
Use its interpreter directly; activation is optional. Flask 3.1.2 was installed
from requirements.txt into the existing environment, and pip check passed.
Git ignore rules were verified for .venv/, .env, .env.local, and Python caches.
The Flask development server is for local development only, not production.

Run from /home/ico/git/PA2577 in one terminal:

```bash
.venv/bin/python services/tasks/app.py
```

Verify in another terminal:

```bash
.venv/bin/python -m pip check
curl --fail-with-body --include http://127.0.0.1:5000/health
```

Expected: no broken requirements, HTTP 200, and {"status":"ok"}.
The startup output was verified to show debug mode off. Stop the server with
Ctrl+C. The service listens only on Pi loopback, not the LAN address.
Stop after TODO 1 and wait for the user's confirmation before TODO 2.

## TODO 2 - Tasks API with PostgreSQL (Verified)

- [x] Inspect host architecture and listening ports read-only: aarch64; no TCP listeners on 5432 or 55432 (2026-10-25).
- [x] Verify Docker client/server access without sudo, Linux ARM64, Compose version, existing containers, and volume inventory; Podman was not found and is not used.
- [x] Obtain explicit approval for the PostgreSQL image, container, dedicated volume, loopback publication, and protected password file only.
- [x] Verify no existing pa2577-postgres container, pa2577-postgres-data volume, or listener on 55432 before creation; no existing resources reused.
- [x] Prepare PostgreSQL with Docker and verify ARM64, readiness, authenticated SQL, dedicated data volume, read-only password file, and loopback-only publication.
- [x] User independently confirmed pg_isready accepts connections and docker port reports 127.0.0.1:55432 -> 5432/tcp.
- [x] Create pa2577_tasks login without superuser, database/role creation, replication, or RLS-bypass privileges; verify restricted project access.
- [x] Configure access through environment variables; add credential-free .env.example and verify .env is ignored and mode 0600.
- [x] Create tasks.tasks: id, title, completed, created_at, with database constraints and administrator ownership.
- [x] Implement GET/POST /api/tasks and PATCH/DELETE /api/tasks/<id>.
- [x] Validate titles and boolean completed; use parameterized SQL and test SQL-like titles as plain data.
- [x] Return appropriate HTTP statuses and useful errors without sensitive internals.
- [x] Preserve GET /health and verify GET /ready checks table/database availability.
- [x] Verify valid/invalid operations over real HTTP and task persistence across a Flask restart: 7 tests passed; rerun confirmed 2026-10-26.

### Earlier Read-Only Findings and Proposal (Superseded by Approved Results Below)

- Host: raspberrypi2, /home/ico/git/PA2577, aarch64. Podman commands could not
  execute: command not found. No installed podman/podman-docker package entry or
  binary in the checked common locations was found. This does not exclude a
  custom installation elsewhere; the user must clarify its location or host.
- Podman version, runtime architecture, rootless operation, containers, images,
  and volumes remain unverified. Do not infer an empty container/volume inventory.
  No Podman installation, image download, container, or volume creation occurred.
- TCP listeners: 22, 53, 2379, 2380, 2381, 5000, 6443, 10248, 10249, 10250,
  10256, 10257, 10259, 32871, 32899, 34867, 36679. UDP: 53, 68, 546, 5353,
  8472, 39259, 40603. Earlier observed Kubernetes NodePorts 30080 and 31674
  remain separate considerations; Kubernetes was not queried or changed here.
- Proposed image: docker.io/library/postgres:17-bookworm, the official PostgreSQL
  image with an explicit major version and Debian variant supporting Linux ARM64.
  Registry availability, the exact ARM64 image digest, and local execution have
  not been verified; do so only after approval. Do not use latest or upgrade
  PostgreSQL major versions against an existing data directory automatically.
- Proposed new container: pa2577-postgres; database: pa2577. Publish TCP only as
  127.0.0.1:55432 -> container 5432 for the Flask service running on the Pi.
  No LAN/public binding. Recheck the port and resource names before creation.
- Proposed new named volume: pa2577-postgres-data mounted at
  /var/lib/postgresql/data for PostgreSQL 17. If that name already exists, stop
  and request a fresh name rather than reusing it. Never mount other projects'
  data. Persistence survives container recreation, not volume deletion or disk
  loss; a volume alone is not a backup.
- Generate a unique database administrator password after approval, without
  logging it or putting it in command arguments or shell history. Prefer a
  Podman secret exposed as a file with POSTGRES_PASSWORD_FILE; verify support
  against the actual Podman version first. Do not use trust authentication.
- Give Flask a separate non-superuser role pa2577_app with only the required
  database/schema/table permissions, not the PostgreSQL administrator role.
  Keep its connection settings in a local ignored .env with owner-only access
  (mode 0600), loaded explicitly when implemented; .env is not loaded yet.
  A future .env.example must contain placeholders only. Never print credentials,
  inspect container environments, or commit secret files.
- Await user clarification of Podman availability and approval of this proposal.
  No database or API implementation is claimed complete.

### Initial Approved PostgreSQL Preparation Results (2026-10-25)

- Scope approved by the user: PostgreSQL preparation only, not the Tasks API,
  application role, schema, or Flask database integration. These were not yet
  implemented at that point; the subsequent approved TODO 2 results follow below.
- Pulled docker.io/library/postgres:17-bookworm explicitly for linux/arm64.
  Local image metadata confirms Linux ARM64. Registry digest:
  sha256:858bb5e98eed02eb8cafbcdc007f9a65d1b613972028944a8ec2133ccaf80d27.
- Created only pa2577-postgres and the new volume pa2577-postgres-data, both
  labeled project=pa2577. The volume is mounted read/write at
  /var/lib/postgresql/data; no other project's data or resources were reused.
- Generated a unique random administrator password locally without displaying
  it or putting its value in commands. .secrets/ has mode 0700 and the password
  file .secrets/postgres-password has mode 0600. .gitignore excludes .secrets/,
  verified by git check-ignore; no secret file is tracked by Git.
- Mounted the password file read-only at /run/secrets/postgres-password and
  configured POSTGRES_PASSWORD_FILE. No literal POSTGRES_PASSWORD was supplied
  in the container configuration. Do not display the file or container environment.
- Initialization explicitly selects SCRAM-SHA-256 for host and local connections.
  SQL verified zero trust rules and zero invalid authentication rules.
- pg_isready accepts connections; container health is healthy. Authenticated
  SQL over TCP succeeded as the administrator against database pa2577 and reports
  PostgreSQL 17.11, data directory /var/lib/postgresql/data, password encryption
  scram-sha-256. No Tasks tables or application role were created at that stage.
- Both Docker configured/active bindings and ss confirm only
  127.0.0.1:55432 -> 5432/tcp. A host loopback TCP connection succeeded.
  The database is not published on 0.0.0.0 or IPv6. External network/firewall
  behavior was not tested; no firewall or Docker configuration was changed.
- The existing bold_ptolemy and tender_franklin containers remain stopped with
  their previous statuses. Kubernetes and PA2595 were not modified.
- Persistence is configured via the named volume. Persistence across container
  recreation or Pi reboot has not been tested, and the volume is not a backup.
  No volumes, containers, or data were deleted. Stop here and await the user.

Non-secret availability check:

```bash
docker exec pa2577-postgres pg_isready -h 127.0.0.1 -p 5432 -U postgres -d pa2577
docker port pa2577-postgres
```

### Tasks API Results and Verification (2026-10-25)

- Existing PostgreSQL/container/volume retained without recreation or restart.
  The user independently confirmed readiness and the loopback port mapping.
- scripts/prepare_tasks_db.py created the dedicated pa2577_tasks role and the
  administrator-owned tasks schema/table in the project database. It refuses an
  existing .env, role, or schema rather than overwriting them; do not rerun it
  as a migration or reset command. Credentials are generated locally, passed to
  administrative SQL on stdin, and never displayed or placed in command arguments.
- Grants: database CONNECT, schema USAGE, table SELECT/DELETE, INSERT/UPDATE
  only for title/completed, and identity-sequence USAGE. No elevated role flags
  or memberships. CREATE/TEMP via PUBLIC were revoked in database pa2577;
  CREATE via PUBLIC was revoked in its public schema. Other databases unchanged.
  Actual denied operations were verified for schema/public/temporary table
  creation, role creation, pg_authid reads, and created_at modification.
- tasks.tasks contains bigint identity id, nonempty varchar(200) title,
  completed boolean default false, and created_at timestamptz default now().
  The application trims titles, enforces 1-200 characters, rejects null
  characters, unknown fields, malformed/empty/non-object JSON, and non-boolean
  completed values. PATCH accepts either or both fields; POST requires title.
- Flask reads project .env with python-dotenv; existing environment variables
  take precedence. It connects only as pa2577_tasks to pa2577, never postgres.
  The local .env has a separate random application password, mode 0600, and
  remains ignored by Git. .env.example contains no password. Do not print .env.
- psycopg 3.2.10 uses parameterized SQL, transaction contexts, a 3-second
  connection timeout and 5-second statement timeout. Database/configuration
  errors return only {"error":"Database unavailable."} with HTTP 503.
- HTTP contract: GET list returns 200 with an array; POST returns 201 with a
  task; PATCH returns 200 with the updated task; DELETE returns empty 204.
  Invalid bodies return JSON errors with 400; absent task IDs return 404.
  GET /health returns 200 independently of the database; GET /ready checks
  actual table access and returns 200 when available, otherwise 503.
- tests/test_tasks_http.py passed all 7 real-HTTP tests, including CRUD, title
  boundaries, SQL-like titles, boolean validation, bad JSON, missing IDs,
  unchanged records after rejected requests, and safe database-unavailable
  responses. It simulated failure only by changing the test Flask process's
  DB_PORT, never by stopping PostgreSQL. Only test-created rows were removed.
- A task's full returned representation survived stopping and starting Flask.
  PostgreSQL/container/volume persistence across recreation or reboot remains
  outside this verification. Statistics was not started or implemented.

### User-Requested Test Rerun (2026-10-26)

- Executed exactly `.venv/bin/python tests/test_tasks_http.py` after confirming
  port 5000 was free; no unknown process was stopped. PostgreSQL remained healthy.
- Actual output: `Ran 7 tests in 5.642s` and `OK` (exit code 0). All seven
  cases passed, including `test_persistence_across_flask_restart`, which creates
  its own task, stops and starts its own Flask process, and confirms the full
  task representation remains available afterward.
- Suite cleanup runs per-test teardown and deletes only IDs created by those
  tests. Independently queried the database afterward: zero titles with the
  suite's `pa2577-http-` marker remained. Port 5000 was free and no test Flask
  process remained after the suite.
- This verifies task persistence across a Flask process restart, not PostgreSQL
  container recreation, volume recovery, or a Pi reboot. No PostgreSQL container
  was recreated or restarted. No API, database, or other project data was deleted.
- No credentials or secrets were displayed. TODO 3 remains untouched.

Run locally from the repository root (debug remains disabled):

```bash
.venv/bin/python services/tasks/app.py
```

Verify from another terminal:

```bash
curl --fail-with-body --include http://127.0.0.1:5000/health
curl --fail-with-body --include http://127.0.0.1:5000/ready
curl --fail-with-body --include http://127.0.0.1:5000/api/tasks
```

Expected: HTTP 200 for each, {"status":"ok"} for health/readiness, and an array
for tasks. To repeat all HTTP checks, first stop the local Flask server with
Ctrl+C so port 5000 is free, then run:

```bash
.venv/bin/python tests/test_tasks_http.py
```

Expected: 7 tests, OK. Tests start/stop their own Flask process on loopback port
5000, restart it for persistence verification, and clean up only their own rows.
Start the normal Flask service again afterward. Stop after TODO 2 and await
the user's confirmation; do not begin Statistics.

## TODO 3 - Statistics Microservice

- [ ] Create services/statistics/app.py on a different local port, such as 5001.
- [ ] Add GET /health and GET /api/statistics.
- [ ] Fetch Tasks GET /api/tasks over HTTP with a timeout; never access PostgreSQL directly.
- [ ] Calculate total, completed, pending counts and handle Tasks unavailability.
- [ ] Verify results against real tasks.

## TODO 4 - Browser Interface (Verified 2026-10-26)

- [x] Serve a simple HTML interface from Tasks: list, add, complete, and delete tasks; display statistics.
- [x] Browser calls only Tasks; Tasks proxies statistics to Statistics, which calls Tasks' list endpoint.
- [x] Verify the configured statistics path is non-recursive: Tasks /api/statistics -> Statistics /api/statistics -> Tasks /api/tasks; task listing never requests statistics.
- [x] Render titles as text using createElement/textContent, not innerHTML, and display useful API errors.
- [x] Verify the complete workflow in a real browser using only uniquely marked test tasks.

### Browser Verification (2026-10-26)

- Tasks serves templates/index.html, static/tasks.css, and static/tasks.js.
  Browser fetches use same-origin Tasks endpoints only. The Tasks statistics
  proxy uses a timeout, rejects redirects, validates counters, and reports safe
  JSON errors; Statistics and its database-free responsibilities were preserved.
- An earlier HTTP regression attempt was blocked by PostgreSQL unavailability,
  not a passing regression. Subsequently, the user explicitly approved starting
  the existing pa2577-postgres container. It was started without recreation,
  volume changes, or deleting data; pg_isready and Tasks /ready then succeeded.
- In the shared real browser at http://127.0.0.1:5000/, verified task listing,
  addition, statistics refresh, completion, updated statistics, and deletion.
  Actual total/completed/pending counters were 5/1/4 before the test, 6/1/5
  after adding its task, 6/2/4 after completion, and 5/1/4 after deletion.
- A unique title containing literal <b>text-only</b> was displayed unchanged
  as text, with no nested b element. All 14 browser requests recorded during
  the successful flow targeted http://127.0.0.1:5000/ only, never Statistics.
- Two initial automation attempts encountered harness limitations (unavailable
  URL global and synchronous checkbox-state checking). Their exact test markers
  were cleaned; the final run used a click followed by waiting for API-confirmed
  counters. All three exact markers were independently verified absent afterward.
  Only test-created records were deleted; the five existing tasks were retained.
- Six focused proxy tests passed: valid contract/destination, listing without
  Statistics calls, invalid upstream data, safe errors, invalid configuration,
  and redirect rejection. Command: .venv/bin/python -m unittest discover
  -s tests -p test_tasks_web.py -v (6 tests, OK).
- Browser API-error rendering was additionally verified with a simulated 503
  for the browser's GET /api/tasks: "Tasks: Database unavailable." appeared.
  The interception was removed, refresh restored real data, and the error cleared.
  No database/service was stopped for that check. The successful CRUD flow used
  real services and PostgreSQL data, not simulated API responses.
- No existing Tasks/Statistics process was stopped. No infrastructure was
  installed, no Kubernetes or PA2595 changes were made, and no commit/push/deploy
  occurred. The only infrastructure action was the separately approved start
  of the existing PostgreSQL container. TODO 5 was not started.
- Security issue remains open: the user changed docker.sock permissions to 0666
  to restore access. This grants all local users effectively root-level Docker
  control and is not a safe configuration. The agent did not make or revert that
  permission change; secure access needs a separate authorized decision.

With the existing local services running, open http://127.0.0.1:5000/ and verify:

```bash
curl --fail-with-body http://127.0.0.1:5000/ready
curl --fail-with-body http://127.0.0.1:5000/api/statistics
.venv/bin/python -m unittest discover -s tests -p test_tasks_web.py -v
```

Expected: readiness {"status":"ok"}, counters matching the task list, and
6 tests passing. Add a uniquely marked task in the browser, complete it, and
delete only that task; counters should return to their initial values.
Stop after TODO 4 and await the user's results before TODO 5.

## TODO 5 - ARM64 Images and Isolated Smoke Tests (Partial)

- [x] Build both Flask images with Gunicorn, debug disabled, and UID/GID 10001:10001.
- [x] Verify both images and running application processes on Linux ARM64.
- [x] Exclude project credentials, .env, .secrets, .git, and .venv from image contents; Statistics contains no psycopg or dotenv.
- [x] Verify isolated HTTP healthchecks, Tasks HTML/static assets, and safe missing-dependency errors, without database credentials or data mounts.
- [x] Publish smoke containers exclusively on loopback with automatically allocated free ports; remove only their temporary containers/network.
- [ ] Complete scripts/smoke_containers.py with exit code 0; final PostgreSQL metadata comparison failed, despite successful HTTP/image checks.
- [ ] TODO 8/9: verify full integration, service DNS, database startup/readiness, and persistent storage through Kubernetes after separate approval.

### Container Results (2026-10-26)

- No Compose file was created or used. No PostgreSQL instance was started,
  recreated, or stopped; no database query or data modification was used for
  these smoke tests. No existing data volume was mounted in a smoke container.
- Added service Dockerfiles using python:3.12-slim-bookworm, Gunicorn 23.0.0,
  two workers/two threads, port 8000, and /health healthchecks. Code remains
  root-owned; the application runs as non-root 10001:10001 with debug off.
- Tasks uses root requirements.txt. Statistics has its own minimal requirements
  containing only Flask and Gunicorn; no database driver or dotenv loader.
  .dockerignore uses an allow-list for application code/assets and dependencies.
- Both native linux/arm64 builds succeeded. Temporary local tags are
  pa2577-tasks:todo5-smoke and pa2577-statistics:todo5-smoke; nothing was pushed.
- Successful HTTP portions of the final smoke attempt used 127.0.0.1:32768
  and 127.0.0.1:32769, assigned by Docker. The Gunicorn PID 1, effective UID/GID,
  debug off, image secret exclusion, dependency checks, and image healthcheck
  commands all passed. Tasks served its page/assets and returned safe 503s
  without DB configuration. Statistics returned a safe 503 for an unreachable
  Tasks upstream. No real cross-service/database integration is claimed.
- Smoke runtime used a dedicated bridge network, read-only root filesystem,
  tmpfs /tmp, all capabilities dropped, no-new-privileges, 256 MiB/1 CPU limits,
  and no secrets, bind mounts, or data volumes. The first internal-network
  attempt did not publish ports with Docker 24 and was cleaned up.
- Initial harness failure: bind mounts do not have the volume Name field.
  After local corrections, both service checks passed, but the final metadata
  snapshot equality assertion failed. This is not a fully passing smoke command;
  no further harness repair was attempted without user direction.
- Read-only follow-up confirmed PostgreSQL ID remains
  bacd64f4f3e549f6a21140c0f556b8dca39322c692c80d541623faa9962fb42c,
  StartedAt 2026-10-26T18:12:56.371321853Z, running=true, OOMKilled=false,
  RestartCount=0, and local Tasks /ready HTTP 200. The exact cause of snapshot
  comparison failure remains unverified; do not claim all metadata was unchanged.
- All own temporary smoke containers/networks were confirmed absent afterward.
  Existing Flask processes were not stopped. No Kubernetes, PA2595, permission,
  commit, push, or deployment changes were made. The Docker socket 0666 security
  issue remains unresolved; this stage did not change its permissions.

Build commands from the repository root:

```bash
docker build --platform linux/arm64 -t pa2577-tasks:todo5-smoke -f services/tasks/Dockerfile .
docker build --platform linux/arm64 -t pa2577-statistics:todo5-smoke -f services/statistics/Dockerfile .
.venv/bin/python scripts/smoke_containers.py
```

The builds passed. The smoke command currently fails its final metadata
comparison; do not mark it successful until repaired and rerun. Full integration
and persistence tests await TODO 8/9. Stop and ask before further repairs or any
deployment; no deployment is authorized by these image/smoke-test instructions.

## TODO 6 - Isolated HTTP Integration (Prepared; Awaiting Execution Approval)

- [x] Inspect existing test targets and local ARM64 Tasks/Statistics/PostgreSQL image metadata read-only.
- [x] Disable the legacy native-target HTTP suites in setUpClass before process startup or API writes; these suites were not run during TODO 6.
- [x] Verify the new runner's default plan and Python syntax without temporary infrastructure or HTTP requests.
- [x] Pass 8 offline safety tests for target validation, topology, mounts, plan-only behavior, and cleanup ownership.
- [ ] Run the prepared isolated HTTP input-validation and error-handling scenarios after approval.
- [ ] Run HTTP integration against the existing images in a new dedicated test network.
- [ ] Verify create -> list -> statistics -> complete -> updated statistics -> delete over HTTP.
- [ ] Verify uniquely identified test records and cleanup restricted to IDs created by the tests.
- [ ] Verify PostgreSQL on temporary tmpfs, no persistent volume/bind mounts, only Tasks published on dynamic loopback, and complete cleanup of this run's resources.

### Prepared Isolation and Approval Gate (2026-10-26)

- scripts/integration_http.py defaults to PLAN ONLY, with no Docker calls, HTTP
  requests, secret generation, or resource creation. Only --execute authorizes
  the prepared script to create resources. It has not been used for this stage.
- Image arguments are configurable: --tasks-image, --statistics-image, and
  --postgres-image default to the existing local ARM64 images listed below.
  Execution inspects local images and uses --pull never; no rebuild or download.
- A fresh UUID determines network pa2577-it-<UUID> and containers
  pa2577-it-<UUID>-tasks, -statistics, and -postgres. Each resource carries the
  pa2577.integration.run=<UUID> label. No existing resource is reused or stopped.
- PostgreSQL uses 256 MiB tmpfs at /var/lib/postgresql/data, no named/anonymous
  volume or host bind, no published port, a new random administrator password,
  SCRAM authentication, and a separate limited Tasks login. Temporary passwords
  are generated in memory and passed via stdin, never printed, placed in command
  arguments, or taken from the application's .env/.secrets. Docker administrators
  can inspect container environments; these are short-lived test credentials only.
- The temporary database is internally named pa2577 with login pa2577_tasks
  because the existing Tasks image requires those names. It is a different server
  on alias db:5432 in the dedicated network, not the native pa2577-postgres server
  or its data. No command targets that existing PostgreSQL container or volume.
- Tasks connects only to db and http://statistics:8000 in that network;
  Statistics receives only http://tasks:8000, without DB/PG credentials.
  Only Tasks publishes 127.0.0.1:<Docker-assigned-free-port>:8000. Statistics and
  PostgreSQL remain unpublished. Runtime limits: apps 256 MiB/1 CPU each,
  PostgreSQL 512 MiB/1 CPU. App root filesystems are read-only with /tmp tmpfs.
- tests/integration_safety.py rejects native ports 5000/5001/5432/55432, remote
  targets, credentials in URLs, unexpected paths, extra network members, wrong
  run labels, persistent/bind mounts, wrong DB/upstream aliases, and any published
  Statistics/PostgreSQL port. Optional --base-url must exactly match this run's
  inspected loopback publication; it cannot select the native application.
- tests/test_isolated_http.py is skipped unless explicitly configured by the
  isolated runner. Mutating requests revalidate the target and Docker topology;
  HTTP proxies and redirects are disabled. Test titles have unique per-run/test
  markers; cleanup deletes only IDs returned by that test's successful POSTs.
- Three HTTP scenarios are prepared: full CRUD/statistics flow, validation and
  SQL-like titles/missing IDs, and safe Statistics-unavailable behavior. The last
  stops/starts only this run's owned Statistics container, never native services
  or PostgreSQL. These scenarios have NOT been executed yet.
- Finally cleanup checks the exact recorded container IDs, names, and run labels
  before removing them, then verifies ownership of the new network before removal.
  It does not use prune, volume deletion, native process control, or Compose.
  Runtime cleanup and tmpfs isolation still require the approved real execution.
- Actual offline validation: 8 tests, OK. An initial offline fixture-placement
  error was corrected and the same safety suite rerun successfully. No legacy
  HTTP suite, temporary container/network, or real database write was executed.
- TODO 5's separate final metadata-comparison failure remains open; this stage
  does not repair or rerun its smoke script. Kubernetes and PA2595 are unchanged.

Safe commands already executed (no infrastructure):

```bash
.venv/bin/python scripts/integration_http.py
.venv/bin/python -m unittest discover -s tests -p test_integration_safety.py -v
```

Proposed command ONLY AFTER USER APPROVAL:

```bash
.venv/bin/python scripts/integration_http.py --execute \
  --tasks-image pa2577-tasks:todo5-smoke \
  --statistics-image pa2577-statistics:todo5-smoke \
  --postgres-image docker.io/library/postgres:17-bookworm
```

Expected, not yet verified: three HTTP scenarios pass and only this run's
containers/network are removed; exit code 0. Preserve failures as failures.
Historical instructions above for test_tasks_http.py/test_statistics_http.py
must not be used against native application data. Both now skip by default.
Stop here pending approval. No CI, Kubernetes integration, or deployment begins.

## TODO 7 - CI Workflow

- [ ] Verify available runner labels, repository access, and any separate registration requirement.
- [ ] Create .github/workflows/ci.yml for pushes to main and manual runs, never external PR code.
- [ ] Build ARM64 application images and start an isolated HTTP test environment without Compose; Kubernetes orchestration requires its separately approved stages.
- [ ] Run HTTP integration tests; publish the exact tested images only after tests pass.
- [ ] Publish to Docker Hub with full commit SHA tags, not only latest.
- [ ] Configure Docker Hub username/token using GitHub Variables/Secrets.
- [ ] Avoid existing app conflicts with unique test resource names and suitable ports.
- [ ] Clean up only the workflow's temporary resources and display the deployable commit SHA.
- [ ] Verify a real CI execution; CI must not change Kubernetes deployments.

## TODO 8 - Kubernetes Configuration (No Deployment)

- [ ] Use namespace pa2577; add Deployment and Service for each Flask service.
- [ ] Inspect StorageClasses and PersistentVolumes before choosing PostgreSQL storage.
- [ ] Explain required Pi preparation and get approval before infrastructure installation.
- [ ] Define PostgreSQL resources and PVC, with a Secret for its password.
- [ ] Add readiness/liveness probes and CPU/memory budgets suitable for 8 GB RAM.
- [ ] Support independent horizontal scaling of both Flask services; keep PostgreSQL at one instance.
- [ ] Select an available exposure port distinct from the previous project's port.
- [ ] Pull application images from Docker Hub, not manually imported images.
- [ ] Validate configuration against existing Kubernetes APIs and explain version limitations; do not deploy.

## TODO 9 - Separate Deployment Workflow

- [ ] Create .github/workflows/deploy.yml with a manual verified-commit-SHA input.
- [ ] Verify CI success for the selected SHA; use configuration and images from that commit without rebuilding.
- [ ] Verify runner cluster access and restrict application changes to namespace pa2577.
- [ ] Prepare any cluster-wide storage separately and explicitly.
- [ ] Wait for rollout/readiness and run HTTP tests against the deployed app; fail on verification errors.
- [ ] Explain rollback to a previous compatible version.
- [ ] Wait for user confirmation before the first execution and verify its results.

## TODO 10 - Assignment Demonstration

- [ ] Demonstrate Tasks at two replicas and verify the app.
- [ ] Separately demonstrate Statistics at two replicas and verify the app.
- [ ] Demonstrate task persistence across PostgreSQL pod recreation without deleting PVC/data.
- [ ] Explain persistence verification after Pi reboot.
- [ ] Explain that replicas on one Pi do not protect against failure of that Pi.

## TODO 11 - Submission Documentation

- [ ] Update README with setup, configuration, verified checks, responsibilities, and REST APIs.
- [ ] Add a Mermaid architecture diagram and GitHub/Docker Hub links.
- [ ] Discuss benefits, challenges, costs, complexity, scaling, and availability.
- [ ] Document implemented security and limitations: authentication, HTTPS, network access, secrets, backups.
- [ ] Acknowledge scaling is unnecessary here; describe an imagined workload that would justify it.
- [ ] Prepare a 5-10 minute presentation script; never claim unverified tests passed.