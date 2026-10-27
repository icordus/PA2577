# PA2577 Helm Chart

This chart is prepared for Kubernetes 1.28 on the ARM64 Raspberry Pi.
It was first deployed after explicit user approval on 2026-10-27.
Release `pa2577`, revision 1, is deployed and passed the HTTP checks below.
Use release name `pa2577` and namespace `pa2577` for the names below.

## Resources

- Namespace `pa2577`, kept on Helm removal to avoid deleting its contents.
- Tasks Deployment and NodePort Service `pa2577-tasks`.
- Statistics Deployment and ClusterIP Service `pa2577-statistics`.
- Single-replica PostgreSQL Deployment, ClusterIP Service, init ConfigMap, and PVC.
- The chart itself creates no Secret, PV, StorageClass, provisioner, host directory, or Helm hook.

Tasks and Statistics use separate `replicaCount` values. PostgreSQL always has
one replica and uses `Recreate`, avoiding an overlapping rolling update.
Only Tasks talks to PostgreSQL. Statistics calls `GET /api/tasks` over HTTP;
Tasks proxies browser statistics requests to Statistics without changing its
task-list endpoint. Statistics health does not depend on Tasks, avoiding a
circular readiness dependency.

## Images

The default Tasks and Statistics Docker Hub tag is the full CI commit SHA:

`5c65f2dcd675a1bc8b6d1b378bd10ba1b999b721`

The repository checklist reports that these exact ARM64 images passed CI and
were published. The running Tasks/Statistics image digests were subsequently
verified to match the published digests. CI was not repeated for deployment.
`imagePullPolicy: Always` requires registry pulls, never manual image imports.
If the repositories are private, supply an existing registry Secret name through
`imagePullSecrets`; do not store registry credentials in chart values.

PostgreSQL uses `docker.io/library/postgres:17-bookworm`. Do not change its major
version on an existing data directory without a separate migration plan.

## External Access

Application URL after the approved first deployment:

`http://192.168.0.71:30081/`

Inspection on 2026-10-27 found NodePorts `30080` and `31674` already allocated.
Port `30081` was free before installation and is now assigned to pa2577-tasks.
The server accepted this port. Other ports in the NodePort range have not been
validated for future use; recheck conflicts before changing the port.

NodePort is not loopback-only: it can expose Tasks on node interfaces. HTTP at
the node's LAN IP was verified from the Pi; access from the user's browser/device
and external firewall/routing remain unverified. There is no authentication or
HTTPS; do not expose this service directly to the Internet. Statistics and
PostgreSQL have no NodePort and are not directly exposed outside the cluster.

## Storage Preparation

Initial read-only inspection found no StorageClasses, PVs, or PVCs. The default claim
requests 2 GiB, `ReadWriteOnce`, `storageClassName: ""`, and the explicit PV name
`pa2577-postgres-pv`. It cannot provision storage automatically. The separately
approved PV now exists and is Bound to the claim after the approved deployment.

Approved storage requirements for this single Pi:

1. Prepare a new, empty directory dedicated to PA2577, outside all existing
   Docker data and other projects. Check free disk space, ownership, and backups.
2. Separately prepare a local PV named `pa2577-postgres-pv`, capacity at least
   2 GiB, no StorageClass, `ReadWriteOnce`, `Retain`, filesystem mode, and node
   affinity for this Pi. Reserve its claim for `pa2577/pa2577-postgres-data`.
3. Ensure the mounted directory supports PostgreSQL UID/GID 999 and fsGroup 999.
   No privileged permission-fixing container is included in this chart.

On 2026-10-27, after separate approvals, the user created
`/var/lib/pa2577/postgresql` with mode 0700 and UID/GID 999:999. Those metadata
were verified without reading or changing the directory contents. The agent
then validated `storage/local-pv.yaml` using server-side dry-run and created
only `pa2577-postgres-pv` with `kubectl create`. The actual PV was verified:
2 GiB, `ReadWriteOnce`, filesystem mode, `Retain`, no StorageClass, local path
above, and node affinity `kubernetes.io/hostname=raspberrypi2`.

The PV was initially `Available`, reserved for `pa2577/pa2577-postgres-data`.
After the separately approved deployment, the PVC and PV are `Bound`, and
PostgreSQL initialized the new data directory successfully. Tasks CRUD passed
against that database. The approved TODO 10 test later verified persistence
across PostgreSQL pod recreation with unchanged PVC/PV UIDs. Persistence after
a Pi reboot and backup/restore remain untested. Existing Docker data was never reused.
The capacity field is not an enforced filesystem quota or reserved disk space.

The PV definition is outside `templates/`, so the Helm chart does not create,
adopt, or delete this separately managed cluster-wide resource. Do not recreate
or change it automatically. All later resource creation still needs approval.

Read-only status check:

```bash
kubectl get pv pa2577-postgres-pv
```

Alternative: approve installation of a local dynamic-storage provisioner, then
adapt this chart's explicit-PV guard and PVC settings. This adds cluster-wide
infrastructure; it is not installed or selected automatically. A simple hostPath
PV is less explicit about node placement and is not the proposed default.

Never reuse the Docker volume `pa2577-postgres-data`, the native container's
directory, or PA2595 data. The similarly named Kubernetes claim is a separate
object backed by newly approved storage. No automatic data migration is included.

The claim has `helm.sh/resource-policy: keep`. This is not a backup or protection
against deliberate deletion. The approved PV must also use `Retain`. Local disk
storage and multiple replicas on one Pi do not survive failure of that Pi.

## Existing Database Secret

The first approved deployment prepared an external Secret in `pa2577`:

- Name: `pa2577-database` (configurable as `postgresql.existingSecret`).
- Key `postgres-password`: a unique administrator password.
- Key `tasks-password`: a different unique password for `pa2577_tasks`.

Distinct new passwords were generated in memory and sent through stdin; no
password was printed, stored in a local file, or committed. No values or Secret
manifest are included. Future password preparation must use
an approved private process, without command-line literals, logs, or committed
files. Do not copy the existing application's credentials.

Tasks receives only `tasks-password`. Statistics receives no database credentials.
PostgreSQL receives both keys to create the limited Tasks role on first startup.
Initialization uses SCRAM for local and host connections; the init SQL reads the
application password from the container environment without embedding it in SQL
files or command arguments. The role has no superuser, database/role creation,
replication, or RLS-bypass privileges; only project table/sequence access is granted.

The init script runs only when the new data directory is empty. Later Secret or
ConfigMap changes do not migrate schema or rotate database passwords. Plan such
changes separately; never delete the PVC to force initialization.

## Probes and Limits

The Flask services run as UID/GID 10001, with read-only root filesystems and a
16 MiB memory-backed `/tmp` for Gunicorn. PostgreSQL runs as UID/GID 999 with
writable PVC data and temporary socket/tmp directories. All containers drop
capabilities, prohibit privilege escalation, use RuntimeDefault seccomp, and do
not mount a service-account token.

Startup/liveness use `/health` for Flask and `pg_isready` for PostgreSQL.
Tasks readiness uses `/ready`, which checks its table through its limited role;
Statistics readiness uses its local `/health`. Database/HTTP timeouts let failed
dependencies return safe errors instead of requiring a startup-order hack.

Default requests are 300m CPU and 448 MiB RAM total at one replica per service;
limits total 2 CPUs and 960 MiB RAM. Initial rollout, image pulls, probes, volume
mounting, database initialization, and service DNS passed. All three pods were
1/1 Ready with zero observed restarts. Resource suitability under load and browser
access from another device remain unverified. The approved TODO 10 scaling and
pod-recreation checks are recorded below; no reboot was performed.

## First Deployment Verification

The approved command was:

```bash
helm install pa2577 helm/pa2577 --namespace pa2577 --wait --timeout 5m
```

It completed with status `deployed`, revision 1. Do not rerun this install against
an existing release or perform upgrades/uninstalls without separate approval.

HTTP checks on the Pi verified the page, /health, /ready, CRUD, statistics, and
invalid input. One uniquely marked task changed total/completed/pending counts
from 0/0/0 to 1/0/1 and 1/1/0, then back to 0/0/0 after deleting only that task.
The actual Tasks process ran as UID/GID 10001 and connected as pa2577_tasks with
no elevated database role flags. No native service or database was changed.

Read-only status and HTTP checks:

```bash
helm status pa2577 --namespace pa2577
kubectl -n pa2577 get deployments,pods,services,pvc
kubectl get pv pa2577-postgres-pv
curl --fail-with-body http://192.168.0.71:30081/ready
curl --fail-with-body http://192.168.0.71:30081/api/statistics
```

Expected: deployed release, available workloads, Bound storage, readiness
{"status":"ok"}, and counters matching the current task list.

## Approved Scaling and Persistence Demonstration

On 2026-10-27, after explicit approval and a read-only comparison with the
installed chart, Tasks was scaled to two replicas alone (Helm revision 2) and
returned to one (revision 3). Statistics was then scaled to two alone (revision 4)
and returned to one (revision 5). Rollouts and HTTP readiness/statistics checks
passed at each two-replica stage; PostgreSQL remained at one replica.

A uniquely marked API task with ID 2 survived deletion and controller recreation
of only the PA2577 PostgreSQL pod. Its complete returned representation was
unchanged. PVC/PV UIDs and binding were unchanged. The test deleted only its own
task afterward and verified statistics returned to their original counts.

The final release is deployed at revision 5, with Tasks/Statistics replica values
1/1 and all three Deployments 1/1 Ready. See the repository TODO.md for pod and
storage UID evidence. No native service, existing Docker volume, other namespace,
or PA2595 data was changed. Do not repeat these mutations without approval.

A future reboot test needs a new retained test task and separate approval before
the user reboots the Pi. After node/service readiness, compare the task and
PVC/PV identities and delete only that task. No reboot test or backup recovery
has been performed; single-node replicas do not protect against failure of the Pi.

## Local Validation Only

Run from the repository root:

```bash
helm lint helm/pa2577 --namespace pa2577 --kube-version 1.28.15 --strict
helm template pa2577 helm/pa2577 --namespace pa2577 --kube-version 1.28.15
```

Independent scaling values were also linted/rendered with
`--set tasks.replicaCount=2 --set statistics.replicaCount=3`. These local checks
were followed by the separately approved live demonstration described above.
Rendering alone checks templates, not live API admission or runtime behavior.
The chart intentionally targets the inspected 1.28 series; it does not upgrade it.

Do not install, upgrade, apply rendered output, provision storage, or create
Secrets until the user approves those steps. The existing `calico-system`
namespace was Terminating during inspection; earlier restart observations were
not diagnosed here. A Ready node is not proof of complete cluster health.