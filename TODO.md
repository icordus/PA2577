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

## TODO 0 - Inspection Complete; Deferred Prerequisites Recorded

- [x] Inspect PA2577 and the previous project, including available instructions.
- [x] Verify the previous project's actual folder and Git remote: PA2595.
- [x] Locate existing workflows, configured runner labels, Dockerfile, and Helm configuration.
- [x] Determine the current terminal host and inspect its listening TCP ports.
- [x] Document reusable patterns and incompatible deployment practices below.
- [x] Create this staged progress checklist.
- [x] Verify Pi Linux ARM64/64-bit and Python version (remote report).
- [x] Verify a working Python virtual environment with pip (remote follow-up report).
- [x] Verify Docker client/server 24.0.6, Linux ARM64 access without sudo, and Compose v2.21.0 (remote follow-up).
- [x] Verify Kubernetes connectivity, node readiness, workloads, and occupied Pi ports (remote report).
- [x] Check PA2577 runner availability in GitHub: user reports "There are no runners configured".
- [ ] Register or grant access to a PA2577 runner and verify its labels, version, and online status in TODO 7.
- [x] Review the user's remote inspection report; record successes and unresolved findings.
- [x] Close the inspection with known failures documented, not marked as successful.

TODOs 1-4 are reported complete on the Pi. Docker is the image builder;
Kubernetes is the orchestrator; do not use Compose. PA2577 has no registered
GitHub runner; address runner access in TODO 7 and do not modify existing runners.

### Verified Local Findings (Mac Inspection)

- Mac workspace: PA2577 is `icordus/PA2577`; previous project is `icordus/PA2595`.
  No repository/ancestor agent instructions were found.
- PA2595 has useful CI, health-probe, and resource-limit examples. Its ML app,
  local-image deployment, and runner configuration are not copied.

### Pi Environment Snapshot (Remote Report)

- Raspberry Pi 4, 8 GB, Ubuntu 22.04, ARM64; Python 3.10.12 and `.venv` work.
- Docker 24.0.6 works without sudo. Kubernetes v1.28.15 server is reachable and
  its node was Ready. Do not upgrade Kubernetes; check current health before use.
- Existing NodePorts 30080 and 31674 are allocated. No StorageClass/PV/PVC was
  reported. Inspect storage before selecting a Kubernetes persistence strategy.
- Two local runner registrations belong to PA2595/PA2579, not PA2577. GitHub
  reports no PA2577 runner. Registration and live-job verification remain TODO 7.
- Reports are historical and remote-provided; recheck relevant state before
  infrastructure changes. Do not reconcile or modify PA2595.

For current diagnostics, rerun only the checks relevant to the active stage on
the Pi. Never share credentials or kubeconfig. A runner shown online is not
verified for PA2577 until an authorized PA2577 job succeeds.

## TODO 1 - First Flask Service (Verified on Pi per Remote Report)

- [x] Create services/tasks/app.py with GET /health returning {"status": "ok"}.
- [x] Run locally on port 5000 with debug disabled; no containers or database yet.
- [x] Add requirements.txt and .gitignore; explain Python virtual environments.
- [x] Verify the running service with curl and review the user's results.

Verified per remote report and user curl: Flask 3.1.2 in `.venv`, debug off,
`GET /health` returns HTTP 200 `{"status":"ok"}`. `.venv`, `.env`, and Python
caches are ignored. Current service state may change; check before starting it.

## TODO 2 - Tasks API with PostgreSQL (Verified per Remote Reports)

- [x] Prepare a separate PostgreSQL database in Docker (user-provided remote preparation report).
- [x] Create a separate non-superuser application role with project-only database/schema privileges.
- [x] Configure access through environment variables; add credential-free .env.example and ignore .env.
- [x] Create tasks schema: id, title, completed, created_at.
- [x] Implement GET/POST /api/tasks and PATCH/DELETE /api/tasks/<id>.
- [x] Validate titles and boolean completed; use parameterized SQL.
- [x] Return appropriate HTTP statuses and useful errors without sensitive internals.
- [x] Add GET /ready to check database availability.
- [x] Verify HTTP operations and persistence across application restart.

### Verification

Remote report: app uses non-superuser `pa2577_tasks`, parameterized SQL, strict
title/boolean validation, safe errors, and env-based configuration (`.env` mode
0600; `.env.example` has placeholders). Seven real-HTTP tests passed, including
CRUD and Flask-process restart persistence; test rows were cleaned up. Database
container/PVC persistence across recreation or Pi reboot remains untested.

PostgreSQL 17 ARM64 runs in `pa2577-postgres`, with dedicated volume
`pa2577-postgres-data`, loopback-only port 55432, SCRAM authentication, and a
0600 ignored secret file. User verified readiness and port mapping. Do not use
the admin account from Flask or delete/recreate this container/volume in tests.

## TODO 3 - Statistics Microservice (Verified per Remote Report)

- [x] Create services/statistics/app.py on port 5001, separate from Tasks.
- [x] Add GET /health and GET /api/statistics.
- [x] Fetch Tasks GET /api/tasks over HTTP with a timeout; Statistics does not access PostgreSQL.
- [x] Calculate total, completed, pending counts and handle Tasks unavailability.
- [x] Verify health, statistics using real Tasks API data, and safe upstream-error handling with HTTP tests (remote report).

Statistics runs separately on port 5001, fetches Tasks over HTTP with timeout,
and has no PostgreSQL access. Three HTTP tests are reported passing. User
verified the Tasks-facing endpoint: total 5, completed 1, pending 4. Detailed
test output is not included in this checklist.

## TODO 4 - Browser Interface (Verified per Remote Agent Report)

- [x] Serve a simple HTML interface from Tasks: list, add, complete, and delete tasks; display statistics.
- [x] Browser calls only Tasks; Tasks proxies statistics to Statistics, which calls Tasks' list endpoint.
- [x] Ensure the statistics request path cannot recurse.
- [x] Render titles as text, not HTML, and display useful API errors.
- [x] Verify the complete workflow in a browser (remote agent reports TODO 4 verified).

Remote agent reports browser CRUD/statistics flow verified. User independently
confirmed `/ready` HTTP 200 and statistics `{total:5, completed:1, pending:4}`;
browser transcript was not provided here.

## TODO 5 - Container Images and Smoke Tests (Partial; No Compose)

- [x] Build both Flask images with Gunicorn, debug disabled, and unprivileged application users (remote report).
- [x] Verify Linux ARM64 image metadata (remote report).
- [x] Omit Docker Compose by user decision; use the existing Kubernetes cluster for orchestration in TODO 8/9.
- [x] Add image health checks and verify reported loopback-only HTTP smoke checks for both containers.
- [ ] Complete scripts/smoke_containers.py; its final existing-PostgreSQL metadata comparison failed, so the test command exited nonzero.
- [ ] Configure service DNS and database startup in Kubernetes manifests, not local Compose.
- [ ] Verify full integrated behavior during the approved Kubernetes deployment; verify persistence without deleting its PVC/data.

Kubernetes is the sole orchestrator; no Compose. Images reportedly build for
ARM64 and pass HTTP/health checks with Gunicorn, UID 10001, and hardened runtime
settings. `scripts/smoke_containers.py` still exits nonzero on a PostgreSQL
metadata comparison; ID/start time stayed the same and restart count was zero,
but cause is unknown. TODO 5 remains partial; rerun only with approval.

## TODO 6 - Automated Tests (In Progress; Integration Isolation Needed)

- [x] Add meaningful input-validation and error-handling tests (existing Tasks/Statistics test suites; previous remote runs reported passing).
- [ ] Run the prepared isolated HTTP integration suite against both app containers and disposable PostgreSQL (not the native services/database).
- [ ] Verify create -> list -> statistics -> complete -> updated statistics -> delete.
- [ ] Use identifiable test records and clean up those records afterward.
- [ ] Isolate the test environment and database volume from application data.

### Test Isolation Findings (Remote Read-Only Inspection, 2026-10-26)

- Legacy HTTP tests target fixed ports 5000/5001 and `.env`, so they can mutate
  application data. Do not run them in their current configuration.
- Prepared suite: `scripts/integration_http.py --execute`; default mode only
  prints a plan. Eight offline safety tests and Python syntax checks reportedly
  pass; no containers have been started for TODO 6.
- Approved design: uniquely named Docker network/containers; disposable
  PostgreSQL on 256 MiB tmpfs; no persistent volume or production credentials;
  Tasks on a dynamic loopback port; Statistics internal via Docker DNS.
  Test create/list/stats/complete/updated-stats/delete, upstream failure, then
  clean only resources labelled for that run. No Compose.
- The `--execute` command is recorded below. It creates infrastructure, so wait
  for explicit approval. The existing PostgreSQL and `pa2577-postgres-data`
  volume must remain untouched.

Command proposed by the Pi agent; not run:

  ```bash
  .venv/bin/python scripts/integration_http.py --execute \
    --tasks-image pa2577-tasks:todo5-smoke \
    --statistics-image pa2577-statistics:todo5-smoke \
    --postgres-image docker.io/library/postgres:17-bookworm
  ```

- HTTP integration and real cleanup remain unverified. No approval to execute
  has been given. The local checklist is not synchronized to the Pi.

## TODO 7 - CI Workflow

- [ ] Verify available runner labels, repository access, and any separate registration requirement.
- [ ] Create .github/workflows/ci.yml for pushes to main and manual runs, never external PR code.
- [ ] Build ARM64 application images and run isolated HTTP integration tests without Compose; use only workflow-owned containers and networks.
- [ ] Run HTTP integration tests; publish the exact tested images only after tests pass.
- [ ] Publish to Docker Hub with full commit SHA tags, not only latest.
- [ ] Configure Docker Hub username/token using GitHub Variables/Secrets.
- [ ] Avoid existing app conflicts with an isolated project name and suitable ports.
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