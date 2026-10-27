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
- [x] Verify full application integration and PostgreSQL persistence through Kubernetes (deployment and pod-recreation evidence in TODO 8/10).

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

## TODO 7 - CI Workflow (Tag Trigger Prepared Locally)

- [x] Register `pa2577-runner`; systemd enabled/active with `self-hosted`, `Linux`, `ARM64` labels; GitHub dispatched and completed a real job.
- [x] Previously verified workflow built and tested ARM64 images and published SHA tags.
- [ ] Switch CI to trigger only on Git tags `v*`; validate semantic version format and keep branch pushes/PRs from triggering it.
- [x] Ten offline safety tests and three isolated HTTP integration tests passed; the integration test used disposable PostgreSQL/tmpfs.
- [x] Publish the exact tested ARM64 image IDs to Docker Hub, tagged with full commit SHA `5c65f2dcd675a1bc8b6d1b378bd10ba1b999b721`.
- [ ] Validate and publish this workflow change; push Git tag `v0.1.0` to publish the tested images with both the version and full SHA tags.
- [x] Job cleanup reported completion; test containers/network/tmpfs were removed. No Kubernetes deployment occurred.
- [x] Docker Hub variable/secret are configured sufficiently for the push to succeed; keep values private.

Published images: `docker.io/icordus/pa2577-tasks:5c65f2dcd675a1bc8b6d1b378bd10ba1b999b721` (digest `sha256:19c74bcc1b9b30f970d2067604226fba9bc3b8b012f602f7f8b04a7147eaa221`) and `docker.io/icordus/pa2577-statistics:5c65f2dcd675a1bc8b6d1b378bd10ba1b999b721` (digest `sha256:3fb3522afc2e0550fbd65e885e7db3275c30c399e09cada455c5933af35a7288`).

Security note: Docker warned that login credentials were stored unencrypted in the job's temporary `DOCKER_CONFIG`; cleanup reported removing it. Document this temporary exposure and cleanup limitation in TODO 11.

## TODO 8 - Helm Chart and First Deployment (Verified per Pi Report, 2026-10-27)

- [x] Inspect storage: no StorageClass/PV/PVC existed; after separate approval, prepare `/var/lib/pa2577/postgresql` (0700, UID/GID 999) and create local PV `pa2577-postgres-pv` (2 Gi, Retain, RWO, node-affinity to raspberrypi2).
- [x] Create `helm/pa2577` with Tasks/Statistics Deployments and Services, one PostgreSQL Deployment, PVC, init ConfigMap, external Secret reference, probes, non-root/read-only security contexts, and resource limits.
- [x] Make Tasks and Statistics replicas independently configurable; Helm lint/template passed for defaults and overrides (2/3 replicas). No live scaling occurred during TODO 8; the approved live demonstration is recorded in TODO 10.
- [x] Initial release uses CI-published full-SHA images; Tasks NodePort 30081 was free before use. Existing NodePorts 30080/31674 were unchanged.
- [x] After explicit approval, create namespace and external Secret, then install release `pa2577` revision 1. All three Deployments were 1/1 Ready; PVC bound to the dedicated PV.
- [x] Verify probes, service DNS, image digests, PostgreSQL initialization, and that Tasks connects as non-superuser `pa2577_tasks`.
- [x] Verify HTTP UI/health/readiness/CRUD/statistics/validation via `http://192.168.0.71:30081`; only the uniquely marked test record was deleted.
- [ ] Confirm browser access from the user's device and evaluate resource budgets under representative load.
- [x] In TODO 10, demonstrate independent scaling and persistence after PostgreSQL pod recreation; results are recorded below.
- [ ] Verify persistence after a separately approved Pi reboot; no reboot has been performed.
- [ ] Publish fixed image tag `v0.1.0` through CI, then separately approve and demonstrate a Helm upgrade using the fixed tag. Current release remains on the existing SHA.

Storage and deployment actions above were separately approved by the user. The existing Docker PostgreSQL/volume, native Flask services, PA2595, and other namespaces were not modified. The local PV's 2 Gi capacity is not a disk quota; alternatives and Secret details are documented in `helm/pa2577/README.md`. No credentials or kubeconfig are in the chart. Evidence is from the Pi agent report; this Mac did not independently run Helm/Kubernetes checks.

## TODO 9 - Manual Helm Deployment Workflow (Prepared Locally; Not Run)

- [x] Prepare manual `.github/workflows/deploy.yml` to read `imageTag` from `helm/pa2577/values.yaml`; no input SHA or CI API dependency.
- [x] Preflight the expected Pi context, namespace, PVC, external Secret, and chart render; upgrade only release `pa2577`, wait for rollouts, and run read-only HTTP checks.
- [x] Use `helm upgrade --install --atomic`; document manual rollback for failures after the Helm operation.
- [ ] Commit/push the workflow, verify runner access in Actions, and execute only after explicit approval. CI is separate; unavailable images cause the rollout to fail.

## TODO 10 - Demonstration (Cluster Checks Verified; Video Pending)

- [x] Separately scale Tasks and Statistics to two replicas through Helm and verify each rollout and HTTP behavior.
- [x] Return each Flask service to one replica before continuing; verify final effective Helm values Tasks=1 and Statistics=1.
- [x] Demonstrate task persistence across PostgreSQL pod recreation without deleting PVC/PV or data; clean up only the test-created task.
- [x] Explain reboot verification and why replicas on one Pi do not protect against failure of that Pi.
- [ ] Perform a separately approved reboot persistence test; it was explained only, not executed.
- [ ] Record a 5-10 minute video: application idea, service roles/API calls, Kubernetes deployment, browser UI, logs, and a brief walkthrough of Kubernetes YAML.

### Approved Cluster Demonstration (2026-10-27)

- Before mutations, checked Helm status, workloads, Services, PVC/PV, effective
	replica values, and the PostgreSQL pod identity. The local chart matched the
	installed manifests; local scaling renders changed only the chosen Deployment's
	replicaCount. The user explicitly approved steps 1-3 and both returns to one.
- Tasks scaling: Helm revision 2 set tasks.replicaCount=2; Tasks was 2/2 Ready
	while Statistics/PostgreSQL stayed 1/1. HTTP /ready returned 200 and statistics
	matched the task list. Revision 3 returned Tasks to 1/1.
- Statistics scaling: revision 4 set statistics.replicaCount=2; Statistics was
	2/2 Ready while Tasks/PostgreSQL stayed 1/1. HTTP statistics matched task data.
	Revision 5 returned Statistics to 1/1. All upgrades used --reuse-values,
	--wait and --timeout 5m, without image rebuilds or changing the database schema.
- Persistence test created one unique pa2577-persistence-<UUID> task through
	the deployed API and retained task ID 2 and its full returned representation.
	The old pod name and UID were verified immediately before deleting only
	pa2577/pa2577-postgres-67dc8cfcdc-gtdvx (UID
	408d00e9-7090-472c-ad54-9594254ecd8b). Its controller created
	pa2577-postgres-67dc8cfcdc-gmhgb (UID bdba9251-05d5-4591-a140-4175959c0fc7).
- Waited for the replacement pod Ready, PostgreSQL rollout, and Tasks /ready.
	The complete saved task representation remained in GET /api/tasks, and
	statistics included it. PVC UID 5f4d905b-38cb-49cf-a502-fa7bb3da079a and
	PV UID 429c8e59-3862-4bd0-b578-21ce8bf9fcdd were unchanged and remained Bound.
- Deleted only task ID 2, confirmed its unique marker was absent, and verified
	counters returned to the original 0 total, 0 completed, 0 pending. No existing
	task, PVC/PV, persistent data, Docker volume, native service, other namespace,
	or PA2595 resource was removed or modified. No Pi reboot, sudo, commit, push,
	CI execution, or deployment-workflow change occurred.
- Final state: release pa2577 deployed, revision 5; Tasks/Statistics/PostgreSQL
	each 1/1 Ready, effective Helm replica values 1/1, PV/PVC Bound, /ready 200,
	and statistics matching task data. The video and reboot checks remain pending.

Approved scaling commands used, with a successful rollout and HTTP check before
each return to one replica:

```bash
helm upgrade pa2577 helm/pa2577 -n pa2577 --reuse-values --set tasks.replicaCount=2 --wait --timeout 5m
helm upgrade pa2577 helm/pa2577 -n pa2577 --reuse-values --set tasks.replicaCount=1 --wait --timeout 5m
helm upgrade pa2577 helm/pa2577 -n pa2577 --reuse-values --set statistics.replicaCount=2 --wait --timeout 5m
helm upgrade pa2577 helm/pa2577 -n pa2577 --reuse-values --set statistics.replicaCount=1 --wait --timeout 5m
```

These are historical commands, not approval for another run. Read-only checks:

```bash
helm status pa2577 -n pa2577
kubectl -n pa2577 get deployments,pods,pvc
kubectl get pv pa2577-postgres-pv
curl --fail http://192.168.0.71:30081/ready
curl --fail http://192.168.0.71:30081/api/statistics
```

Expected final state: three 1/1 Ready Deployments, PV/PVC Bound, readiness
{"status":"ok"}, and statistics matching the current tasks, not necessarily
zero if the user later adds tasks.

For a future reboot test, obtain separate approval, create a new uniquely marked
task through the API, and retain its ID and returned fields before the user
reboots the Pi. After the node/services are Ready, verify the same PVC/PV identity
and task representation, then delete only that test task. Do not delete storage
or change credentials. This has not been executed. Multiple replicas on this
single Pi improve process-level availability, not protection against loss of
the Pi, disk, power, or network. A retained local PV is not a backup.

Stop after TODO 10; do not begin TODO 11 without user direction.

## TODO 11 - Submission Documentation (Not Started)

- [ ] Update README with setup/configuration, component responsibilities, APIs, and a Mermaid architecture diagram.
- [ ] Include GitHub/Docker Hub links; discuss benefits, challenges, costs, complexity, scaling, and availability.
- [ ] Document security and limitations: authentication, HTTPS, network access, secrets, backups.
- [ ] Acknowledge this app does not need scaling; describe a hypothetical workload that would.
- [ ] Prepare a concise presentation outline and likely Q&A on architecture, business trade-offs, service interaction, deployment, and security; never claim an unverified result.
