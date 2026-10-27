# PA2577 Helm Chart

This chart is prepared for Kubernetes 1.28 on the ARM64 Raspberry Pi.
It has only been linted and rendered locally. Nothing has been deployed.
Use release name `pa2577` and namespace `pa2577` for the names below.

## Resources

- Namespace `pa2577`, kept on Helm removal to avoid deleting its contents.
- Tasks Deployment and NodePort Service `pa2577-tasks`.
- Statistics Deployment and ClusterIP Service `pa2577-statistics`.
- Single-replica PostgreSQL Deployment, ClusterIP Service, init ConfigMap, and PVC.
- No Secret, PV, StorageClass, provisioner, host directory, or Helm hook is created.

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
were published. This preparation did not repeat CI or query the registry.
`imagePullPolicy: Always` requires registry pulls, never manual image imports.
If the repositories are private, supply an existing registry Secret name through
`imagePullSecrets`; do not store registry credentials in chart values.

PostgreSQL uses `docker.io/library/postgres:17-bookworm`. Do not change its major
version on an existing data directory without a separate migration plan.

## External Access

Proposed URL after an approved successful deployment:

`http://192.168.0.71:30081/`

Inspection on 2026-10-27 found NodePorts `30080` and `31674` already allocated.
No Service or host TCP listener used `30081`. This is not a reservation: recheck
before deployment. The chart assumes the standard NodePort range 30000-32767;
the actual API-server range has not been independently checked.

NodePort is not loopback-only: it can expose Tasks on node interfaces. Firewall,
LAN routing, and browser access remain untested. There is no authentication or
HTTPS; do not expose this service directly to the Internet. Statistics and
PostgreSQL have no NodePort and are not directly exposed outside the cluster.

## Storage Preparation

Initial read-only inspection found no StorageClasses, PVs, or PVCs. The default claim
requests 2 GiB, `ReadWriteOnce`, `storageClassName: ""`, and the explicit PV name
`pa2577-postgres-pv`. It cannot provision storage automatically. The separately
approved PV now exists, but PVC binding has not been tested or performed.

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

The PV is `Available`, with claimRef reserving it for
`pa2577/pa2577-postgres-data` but no claim UID yet. No PVC, namespace, Secret,
pod, or deployment was created. Available does not mean mounted or tested with
PostgreSQL. Directory contents, data persistence, and mounting remain unverified.
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

Before an approved deployment, prepare an existing Secret in `pa2577`:

- Name: `pa2577-database` (configurable as `postgresql.existingSecret`).
- Key `postgres-password`: a unique administrator password.
- Key `tasks-password`: a different unique password for `pa2577_tasks`.

No values or Secret manifest are included. Generate and supply passwords using
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
limits total 2 CPUs and 960 MiB RAM. Resource suitability, volume permissions,
image pulls, DNS, probes, initialization, external access, and persistence still
need runtime validation after an approved deployment.

## Local Validation Only

Run from the repository root:

```bash
helm lint helm/pa2577 --namespace pa2577 --kube-version 1.28.15 --strict
helm template pa2577 helm/pa2577 --namespace pa2577 --kube-version 1.28.15
```

Independent scaling values were also linted/rendered with
`--set tasks.replicaCount=2 --set statistics.replicaCount=3`. No live scaling
occurred. Rendering checks templates, not live API admission or runtime behavior.
The chart intentionally targets the inspected 1.28 series; it does not upgrade it.

Do not install, upgrade, apply rendered output, provision storage, or create
Secrets until the user approves those steps. The existing `calico-system`
namespace was Terminating during inspection; earlier restart observations were
not diagnosed here. A Ready node is not proof of complete cluster health.