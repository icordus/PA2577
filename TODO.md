# PA2577 Task Manager Progress

Work one stage at a time. After each stage, report changes, verification commands/results, and wait before continuing. Check items only after verification.

## Working Rules

- Do not modify PA2595, commit/push/deploy automatically, or run `sudo`.
- Do not upgrade Kubernetes or delete existing data, volumes, or cluster resources.
- Explain infrastructure changes and obtain approval before creating/running them.
- Never commit credentials, `.env`, or kubeconfig. Do not print secrets.
- Kubernetes is the orchestrator. Do not create or use Docker Compose.
- Use Docker for ARM64 image builds and isolated smoke/integration tests only.

## TODO 0 - Inspection (Closed)

- [x] Confirmed previous project is `icordus/PA2595`; leave it unchanged.
- [x] Inspected repository instructions and available workflows/container/Kubernetes configuration.
- [x] Confirmed Raspberry Pi 4, Ubuntu 22.04, ARM64, Python 3.10, Docker 24.0.6, Kubernetes client/server 1.28.5/1.28.15.
- [x] Confirmed Kubernetes access/node readiness at inspection time. Recheck health before future changes; Kubernetes 1.28 is unsupported upstream and must not be upgraded for this project.
- [x] Initial inspection found no PA2577 runner; user subsequently registered `pa2577-runner` with `self-hosted`, `Linux`, `ARM64` labels and enabled its systemd service.
- [x] Decided Kubernetes replaces Compose; plain Kubernetes manifests are sufficient.

Environment notes: Existing project NodePorts 30080/31674 were allocated; no StorageClass/PV/PVC was reported. Inspect storage before choosing a Kubernetes persistence method. Reports are historical and came from the Pi; this Mac checklist is not automatically synchronized there.

## TODO 1 - First Flask Service (Verified)

- [x] `services/tasks/app.py`: `GET /health` returns `{"status":"ok"}`.
- [x] Local port 5000, debug disabled; `requirements.txt` and `.gitignore` added.
- [x] Flask 3.1.2 in `.venv`; `pip check` passed; user verified HTTP 200 on Pi.

## TODO 2 - Tasks API and PostgreSQL (Verified per Pi Reports)

- [x] Separate PostgreSQL 17 ARM64 container `pa2577-postgres`, database `pa2577`, volume `pa2577-postgres-data`.
- [x] PostgreSQL published only on `127.0.0.1:55432`; SCRAM authentication and ignored mode-0600 secret file.
- [x] Non-superuser `pa2577_tasks` role; Flask uses environment configuration, `.env` mode 0600, credential-free `.env.example`.
- [x] `tasks.tasks` schema and CRUD endpoints: `GET/POST /api/tasks`, `PATCH/DELETE /api/tasks/<id>`.
- [x] Parameterized SQL, title/boolean validation, safe errors, `/ready` database check.
- [x] Seven real-HTTP tests passed, including task persistence across Flask restart; test rows were cleaned up.

PostgreSQL container/volume persistence across recreation or reboot remains unverified. Never use the administrator account from Flask or delete/recreate the existing container/volume in tests.

## TODO 3 - Statistics (Verified per Pi Reports)

- [x] Separate Flask service on port 5001 with `/health` and `/api/statistics`.
- [x] Calls Tasks over HTTP with a timeout; no PostgreSQL access. Handles invalid/unavailable upstream responses.
- [x] Three tests reported passing. User verified counts: 5 total, 1 completed, 4 pending.

## TODO 4 - Browser Interface (Verified per Remote-Agent Report)

- [x] Tasks-served page supports list/add/complete/delete and statistics.
- [x] Browser calls only Tasks; Tasks proxies Statistics, which calls Tasks' list endpoint. No recursion.
- [x] Titles rendered as text; useful API errors shown.
- [x] Remote agent reports browser CRUD flow verified. Detailed browser transcript was not included in this Mac session.

## TODO 5 - ARM64 Images and Smoke Tests (Partial)

- [x] Tasks and Statistics images built for Linux ARM64, Gunicorn, non-root UID/GID 10001, image healthchecks.
- [x] Reported isolated loopback HTTP/health checks passed; no Compose used.
- [ ] Repair and rerun `scripts/smoke_containers.py`: its final PostgreSQL metadata comparison failed although container ID/start time were unchanged and restart count was zero. Cause remains unknown.
- [ ] Complete integration/persistence verification through Kubernetes in TODO 8/9.

Security note: Pi report says Docker socket permissions were changed to `0666`; this gives local users effectively root-level Docker control. The agent did not make that change. Review separately; do not change permissions automatically.

## TODO 6 - Isolated HTTP Integration (Verified on Pi, 2026-10-27)

- [x] Input-validation/error-handling coverage exists.
- [x] Real HTTP integration with disposable PostgreSQL; create/list/statistics/complete/updated-statistics/delete.
- [x] Unique test records cleaned up; test database isolated on 256 MiB tmpfs with no persistent volume.
- [x] Only Tasks published on a dynamic loopback port; Statistics internal over Docker DNS; no Compose.
- [x] Independent cleanup check found no integration-labelled containers, networks, or volumes.

Reported command result: `Ran 3 tests in 20.234s`, `OK`, target `127.0.0.1:32771`. Existing native services, PostgreSQL container, and `pa2577-postgres-data` were not accessed or changed. Evidence is from the Pi-agent report, not an independent run on this Mac.

### Recorded Pi Integration Runs

- The isolated HTTP suite passed three tests on both 2026-10-26 and 2026-10-27; the latest took 20.234s. Both runs reported cleanup of only their temporary Docker network/containers and PostgreSQL tmpfs. No application database, persistent volume, Kubernetes, or PA2595 was touched.

## TODO 7 - CI Workflow (Verified, 2026-10-27)

- [x] Register `pa2577-runner`; systemd enabled/active with `self-hosted`, `Linux`, `ARM64` labels; GitHub dispatched and completed a real job.
- [x] CI runs on push to `main` and manual dispatch only, not pull requests.
- [x] Ten offline safety tests and three isolated HTTP integration tests passed; the integration test used disposable PostgreSQL/tmpfs.
- [x] Publish the exact tested ARM64 image IDs to Docker Hub, tagged with full commit SHA `5c65f2dcd675a1bc8b6d1b378bd10ba1b999b721`.
- [x] Job cleanup reported completion; test containers/network/tmpfs were removed. No Kubernetes deployment occurred.
- [x] Docker Hub variable/secret are configured sufficiently for the push to succeed; keep values private.

Published images: `docker.io/icordus/pa2577-tasks:5c65f2dcd675a1bc8b6d1b378bd10ba1b999b721` (digest `sha256:19c74bcc1b9b30f970d2067604226fba9bc3b8b012f602f7f8b04a7147eaa221`) and `docker.io/icordus/pa2577-statistics:5c65f2dcd675a1bc8b6d1b378bd10ba1b999b721` (digest `sha256:3fb3522afc2e0550fbd65e885e7db3275c30c399e09cada455c5933af35a7288`).

Security note: Docker warned that login credentials were stored unencrypted in the job's temporary `DOCKER_CONFIG`; cleanup reported removing it. Document this temporary exposure and cleanup limitation in TODO 11.

## TODO 8 - Kubernetes Configuration (Not Started; Do Not Deploy)

- [ ] Create a minimal Helm chart (for example `helm/pa2577`) for namespace `pa2577`, with Tasks and Statistics Deployments/Services and separate PostgreSQL/PVC resources.
- [ ] Inspect StorageClasses/PVs first; explain Pi preparation and obtain approval before infrastructure changes.
- [ ] Use a Kubernetes Secret for the database password, readiness/liveness probes, and suitable CPU/memory requests/limits.
- [ ] Expose the UI/API from outside the cluster using an available Service/NodePort; verify browser access.
- [ ] Make both Flask replica counts independently configurable in Helm values; keep PostgreSQL at one instance.
- [ ] Pull application images from Docker Hub using full-SHA tags; never rely on manually imported images.
- [ ] Validate with `helm lint` and `helm template` against the existing Kubernetes API version. Do not install/upgrade the release in this stage.

## TODO 9 - Deployment Workflow (Not Started)

- [ ] Add manual `.github/workflows/deploy.yml` requiring a commit SHA whose CI passed; use that commit's manifests/images without rebuilding.
- [ ] Verify runner cluster access; scope changes to namespace `pa2577` except explicitly approved cluster-wide storage preparation.
- [ ] Wait for rollout/readiness, run HTTP checks, fail on verification errors, and document rollback.
- [ ] Obtain explicit user confirmation before the first deployment.

## TODO 10 - Demonstration (Not Started)

- [ ] Separately scale Tasks and Statistics to two replicas and verify each.
- [ ] Demonstrate task persistence across PostgreSQL pod recreation without deleting the PVC/data; explain reboot verification.
- [ ] Explain that replicas on one Pi do not protect against failure of that Pi.
- [ ] Record a 5-10 minute video: application idea, service roles/API calls, Kubernetes deployment, browser UI, logs, and a brief walkthrough of Kubernetes YAML.

## TODO 11 - Submission Documentation (Not Started)

- [ ] Update README with setup/configuration, component responsibilities, APIs, and a Mermaid architecture diagram.
- [ ] Include GitHub/Docker Hub links; discuss benefits, challenges, costs, complexity, scaling, and availability.
- [ ] Document security and limitations: authentication, HTTPS, network access, secrets, backups.
- [ ] Acknowledge this app does not need scaling; describe a hypothetical workload that would.
- [ ] Prepare a concise presentation outline and likely Q&A on architecture, business trade-offs, service interaction, deployment, and security; never claim an unverified result.
