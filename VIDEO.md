# PA2577 Video Script

Target length: 6-8 minutes. Record the screen with voice-over. Replace `<NODE_IP>` with the node address when showing commands; do not show credentials or Secret contents.

## 1. Introduction - 30 seconds

**Show:** README title or the running application.

> PA2577 is a task management application designed to demonstrate how a small web application can be built and operated using cloud-native practices. Users can create, update, complete, and delete tasks, while a separate service calculates task statistics. PostgreSQL stores the data persistently. Kubernetes and Helm manage the services and storage, and a CI workflow builds and tests the application images. The project also explores the trade-off: this architecture is useful for demonstrating independent services and deployment, but it is more complex than this small application strictly needs.

## 2. Architecture - 30 seconds

**Show:** The architecture diagram in README.md.

> Here is the application architecture. The browser connects to the Tasks Service, which routes requests to the Tasks Deployment. Tasks serves the interface and API, and it is the only application service that accesses PostgreSQL. For statistics, Tasks calls the Statistics Service; Statistics then requests the task list from Tasks and calculates the totals. PostgreSQL runs as a separate Deployment and stores its data through a PVC connected to a local PV. The services and PVC are in the `pa2577` namespace; the PV is scoped to the Kubernetes cluster.

## 3. User Interface - 1 minute

**Show:** The task list, counters, and add/edit/complete/delete controls.

> The interface lets users manage tasks and see total, completed, and pending counts. The current source uses server-rendered Jinja templates, HTML forms, and CSS, so it does not need JavaScript or a frontend build tool. The version currently deployed on the Pi is `v0.1.0`; this newer JavaScript-free interface is local and has not yet been deployed. I will not present the local preview as the deployed application.

If demonstrating CRUD against the deployed database, obtain approval first, create only a clearly marked demo task, and delete only that task after the demonstration. Otherwise, show the existing task data without changing it.

## 4. Kubernetes and Helm - 1 minute

**Show:** Helm status and workload/storage summaries. Do not show Secrets.

```bash
helm status pa2577 -n pa2577
kubectl -n pa2577 get deployments,pods,services,pvc
kubectl get pv pa2577-postgres-pv
```

> Helm manages the three Deployments and their Services in the `pa2577` namespace. Tasks is reachable through NodePort 30081; Statistics and PostgreSQL use internal Services. PostgreSQL uses a PVC in the namespace, bound to a local PV. The PV is cluster-scoped, so it is outside the namespace. The chart also configures health probes and independently configurable replica counts for Tasks and Statistics.

## 5. CI and Deployment - 1 minute

**Show:** The CI and deploy workflows, then the successful Actions run.

> CI runs when a version tag is pushed. It builds ARM64 images, tests the images with isolated disposable PostgreSQL, and publishes version and commit-SHA tags to Docker Hub. CI does not deploy. Deployment is a separate manual workflow: it validates the existing cluster resources, upgrades the Helm release, and checks rollouts, images, storage, and read-only HTTP endpoints. The recorded `v0.1.0` deployment completed as Helm revision 6. The current local UI changes still need a new image version and a separately approved deployment.

## 6. Scaling and Persistence - 1 minute

**Show:** The historical scaling results and persistence notes in TODO.md; do not rerun cluster mutations for the video.

> In the earlier demonstration, Tasks and Statistics were each scaled to two replicas independently, then returned to one. A uniquely marked test task also survived recreation of the PostgreSQL pod, while the PVC and PV remained bound. This demonstrates process-level scaling and pod-recreation persistence, but it does not prove protection against failure of the node or disk.

## 7. Limitations and Conclusion - 1 minute

**Show:** The README limitations and benefits.

> This is a course demonstration, not a production high-availability system. It uses one node and local storage. Reboot persistence, backup and restore, and representative load have not been verified. The NodePort uses unauthenticated HTTP and is intended only for a trusted lab network. The project demonstrates service separation, persistent storage, CI, and repeatable Helm deployment, while also showing the extra operational complexity those choices introduce.

## Recording Checklist

- Record for 5-10 minutes and make sure the narration is audible.
- Hide notifications and any terminal history or page containing credentials.
- Never show `.env`, Docker tokens, kubeconfig, or Kubernetes Secret values.
- Use read-only cluster commands in the recording; do not trigger CI, deploy, scale, reboot, or mutate live data just for the video.
- State clearly which interface/version is deployed and which is only local.
