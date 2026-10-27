# PA2577 Task Manager Progress

Work one stage at a time. After each stage, report changes, verification commands/results, and wait before continuing. Check items only after verification.

## Working Rules

- Do not modify PA2595, commit/push/deploy automatically, or run `sudo`.
- Do not upgrade Kubernetes or delete existing data, volumes, or cluster resources.
- Explain infrastructure changes and obtain approval before creating/running them.
- Never commit credentials, `.env`, or kubeconfig. Do not print secrets.
- Kubernetes is the orchestrator. Manage PA2577 resources through a Helm chart; do not create or use Docker Compose.
- Use Docker for ARM64 image builds and isolated smoke/integration tests only.

## TODO 0 - Inspection (Closed)

- [x] Confirmed previous project is `icordus/PA2595`; leave it unchanged.
- [x] Inspected repository instructions and available workflows/container/Kubernetes configuration.
- [x] Confirmed Raspberry Pi 4, Ubuntu 22.04, ARM64, Python 3.10, Docker 24.0.6, Kubernetes client/server 1.28.5/1.28.15.
- [x] Confirmed Kubernetes access/node readiness at inspection time. Recheck health before future changes; Kubernetes 1.28 is unsupported upstream and must not be upgraded for this project.
- [x] Initial inspection found no PA2577 runner; user subsequently registered `pa2577-runner` with `self-hosted`, `Linux`, `ARM64` labels and enabled its systemd service.
- [x] Decided Kubernetes replaces Compose; TODO 8 subsequently selects a Helm chart rather than separately managed manifests.

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

## TODO 8 - Helm Chart (First Approved Deployment Verified over HTTP)

- [x] Initial storage inspection found no StorageClass, PV, or PVC. Node raspberrypi2 was Ready, ARM64, with no taints; API server is v1.28.15. Separately approved PV creation is recorded below.
- [x] Prepare helm/pa2577 with namespace pa2577, Tasks/Statistics Deployments and Services, and separate single-replica PostgreSQL with PVC and init ConfigMap.
- [x] Reference an externally prepared Kubernetes Secret; include probes, non-root security contexts, read-only root filesystems, and CPU/memory budgets. No password or Secret resource is included.
- [x] Verify Tasks NodePort 30081 was free before deployment and is now allocated only to pa2577-tasks; existing NodePorts 30080/31674 are left unchanged.
- [x] Lint/render independent Tasks and Statistics replicaCount values (2 and 3); PostgreSQL remains fixed at one replica with Recreate strategy.
- [x] Reference reported CI-tested Docker Hub images using full SHA 5c65f2dcd675a1bc8b6d1b378bd10ba1b999b721 and imagePullPolicy Always; no manual imports.
- [x] Run helm lint --strict and helm template locally with --namespace pa2577 --kube-version 1.28.15; 1 chart linted, 0 failed. Also passed with the independent scaling overrides.
- [x] Obtain separate user approvals for the dedicated local-PV strategy, administrative directory preparation, and creation of only the cluster-wide PV.
- [x] Verify the user-prepared /var/lib/pa2577/postgresql directory metadata: mode 0700, UID/GID 999:999; no agent permission or data changes.
- [x] Create and verify pa2577-postgres-pv: 2Gi, Retain, ReadWriteOnce, filesystem, no StorageClass, local path, node affinity raspberrypi2; initially Available, now Bound to pa2577/pa2577-postgres-data.
- [x] Obtain explicit user approval for namespace, external Secret, and the first Helm deployment; create new credentials without displaying or saving them locally.
- [x] Install release pa2577, revision 1, using the existing chart and CI-tested images; verify all three Deployments available 1/1 with zero pod restarts.
- [x] Verify PVC/PV binding, initial database/schema setup, probes, service DNS, running image digests, and the actual non-superuser Tasks login.
- [x] Verify page, health/readiness, CRUD/statistics and invalid-input handling through http://192.168.0.71:30081; remove only the unique test record.
- [ ] Confirm browser access from the user's device and assess resource budgets under representative load.
- [ ] Verify independent live scaling and persistence after PostgreSQL pod recreation/reboot in TODO 10; these checks have not been performed.

Initial approved storage preparation (2026-10-27): the user created the dedicated directory /var/lib/pa2577/postgresql with mode 0700 and UID/GID 999:999. No existing PV/PVC name conflicts were found. The agent server-dry-run validated and then created only the 2Gi local PV pa2577-postgres-pv using helm/pa2577/storage/local-pv.yaml, outside the chart templates. At that point its phase was Available, with claimRef pa2577/pa2577-postgres-data without a claim UID, and no namespace, PVC, Secret, pod, or deployment existed. No directory contents were read or changed during that preparation. The 2Gi capacity is not an enforced disk quota. The subsequently approved first deployment is recorded below.

Alternative storage provisioners still require separate approval and are not an automatic fallback. See helm/pa2577/README.md for Secret key names, retention limits, and validation commands. No Secret values or kubeconfig were displayed.

### First Approved Helm Deployment (2026-10-27)

- The user explicitly selected approval for namespace, Secret, and the first Helm deployment. Preflight found no existing release/namespace, the PV was Available, the node was schedulable, and NodePort 30081 was free.
- Created namespace pa2577 with Helm ownership metadata, then external Secret pa2577-database with distinct new postgres-password/tasks-password values generated in memory and sent via stdin. No password was printed or written to local files/Git. The chart references but does not manage this Secret.
- Executed `helm install pa2577 helm/pa2577 --namespace pa2577 --wait --timeout 5m`. Result: STATUS deployed, REVISION 1. No automatic deletion or rollback flags were used.
- All Deployments rolled out: Tasks, Statistics, and PostgreSQL are each 1/1 Ready/Available, with zero observed pod restarts. PVC pa2577-postgres-data is Bound to the dedicated pa2577-postgres-pv; Retain remains in effect.
- Running Tasks/Statistics image digests match the CI-published digests recorded in TODO 7. Both use full SHA 5c65f2dcd675a1bc8b6d1b378bd10ba1b999b721. PostgreSQL uses the expected official image digest. No image was rebuilt or manually imported.
- From the actual Tasks container, verified effective UID/GID 10001, current_user pa2577_tasks, database pa2577, and all elevated role flags false. Successful HTTP statistics calls verify the configured in-cluster service path and initialized task table.
- NodePort HTTP checks from the Pi passed for /, /health, /ready, task create/list/complete/delete, statistics, invalid title, and invalid completed value. Total/completed/pending were 0/0/0 -> 1/0/1 -> 1/1/0 -> 0/0/0. Only the uniquely marked verification task was deleted, and its absence was confirmed.
- PostgreSQL initialization wrote only to the newly approved Kubernetes PV. The existing native Docker PostgreSQL/data, native Flask services, PA2595, and other namespaces were not modified. No sudo, commit, push, CI execution, or deployment workflow creation occurred.
- External browser access from the user's device, independent scaling, pod-recreation/reboot persistence, backup/restore, and load/resource suitability remain unverified. Stop and wait for the user's results before further changes.

## TODO 9 - Deployment Workflow (Not Started)

- [ ] Add manual `.github/workflows/deploy.yml` requiring a commit SHA whose CI passed; use that commit's Helm chart/values and images without rebuilding.
- [ ] Verify runner cluster access; scope changes to namespace `pa2577` except explicitly approved cluster-wide storage preparation.
- [ ] Wait for rollout/readiness, run HTTP checks, fail on verification errors, and document rollback.
- [x] Obtain explicit confirmation before the first manual Helm deployment (recorded in TODO 8); the deployment workflow is still not implemented and its first execution needs separate approval.

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
