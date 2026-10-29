# PA2577 Task Manager Progress

## Working Rules

- Do not modify PA2595, run `sudo`, or commit/push/deploy automatically.
- Get approval before infrastructure changes, reboot, scaling, or live mutation tests.
- Never delete existing data/PVC/PV/volumes or expose credentials.
- Use Kubernetes/Helm, not Docker Compose. Check items only after verification.

## Completed

- [x] Tasks CRUD API, input validation, parameterized SQL, and restricted PostgreSQL login.
- [x] Statistics service uses Tasks over HTTP and has no database access.
- [x] ARM64 images with Gunicorn, non-root users, and healthchecks.
- [x] Helm chart with three Deployments, Services, probes, external Secret, and PVC/local PV.
- [x] Tag-only CI with isolated integration, version/SHA publication, and job-scoped cleanup.
- [x] Manual deploy from the selected branch, without a CI API dependency.
- [x] Deploy `v0.1.0`, revision 6: rollouts, image tags, PVC, and read-only HTTP checks passed.
- [x] Earlier Pi demonstration: scale each Flask service to two replicas, then return to one.
- [x] Earlier Pi demonstration: task survived PostgreSQL pod recreation; PVC/PV identities were unchanged, and only the test-created task was cleaned up.
- [x] Live HTTP and LAN browser access verified from this Mac on 2026-10-27.
- [x] Replace JavaScript with Jinja templates, HTML forms, and CSS locally; keep REST APIs unchanged.
- [x] Local web tests cover forms, escaping, service errors, same-origin protection, and JSON API compatibility.
- [x] Browser CRUD works with JavaScript disabled and simulated dependencies; desktop/mobile layout checked, with no horizontal overflow.
- [x] Simplify README/TODO while preserving architecture, setup, CI/deploy, and limitations.
- [x] Update the Helm chart compatibility range to Kubernetes 1.32 after the user's cluster-upgrade report; local lint/render validation is recorded below.

## Evidence

- [Deploy run 40537098402](https://github.com/icordus/PA2577/actions/runs/40537098402): `v0.1.0`, revision 6. This is the deployed baseline, not the new server-rendered UI.
- Earlier Pi integration: 3 HTTP tests passed with PostgreSQL on temporary tmpfs; cleanup was reported complete.
- Earlier scaling: revisions 2/3 increased/reset Tasks; revisions 4/5 increased/reset Statistics. Both returned to one replica before revision 6.
- Previous local review: 16 safety tests, 5 deployment-validator tests, Helm lint/template, and Bash/YAML checks passed.
- Current local suite: 38 tests passed, including 17 web tests; 3 live-test suites were intentionally skipped. No live database writes, image build, or deployment was performed for this change.
- User reports upgrading the cluster to Kubernetes 1.32 on 2026-10-29. This workspace has not independently queried the cluster; the chart now targets the 1.32 minor series.
- Local `.venv` contains the existing project dependencies; no Node or frontend build dependencies are needed.

## To Deliver

- [ ] Run isolated HTTP integration on ARM64 for the changed application after approval.
- [ ] Publish a new, unused version through CI and record its run and version/SHA image references. Do not overwrite `v0.1.0`.
- [ ] After approval, deploy the new server-rendered UI and verify its browser CRUD flow.
- [ ] Record the CI run proving how the existing `v0.1.0` tags were published; successful deployment alone does not establish provenance.
- [ ] Record and link the required 5-10 minute video using the [VIDEO.md](VIDEO.md) script: UI, architecture, Kubernetes resources/YAML, CI/deploy, scaling, and persistence evidence.

## Known Limitations

- Legacy [smoke_containers.py](scripts/smoke_containers.py) still has an unresolved final PostgreSQL metadata comparison failure; do not mark it passed.
- Pi reboot persistence, backup/restore, and representative load are untested. Native Docker database-volume recreation persistence is also unverified.
- One Pi/local PV is not high availability, and `Retain` is not a backup. Storage preparation is in the [chart guide](helm/pa2577/README.md).
- Unauthenticated HTTP NodePort is for the trusted lab network only; HTTPS and production firewall policy are not configured.
- Alternate-branch deploy is supported by configuration but has not been demonstrated. The revision-6 upgrade did not independently test data persistence across that upgrade.

Detailed earlier reports remain in Git history. Do not treat historical evidence
as verification of the new UI or approval to rerun mutating commands.
