# gitops-demo-app

A FastAPI application and its CI pipeline — one half of a two-repository GitOps CI/CD demonstration.

## Hands-On Ownership

I designed, built, and validated this application repository and its CI pipeline end-to-end, including the cross-repository handoff into the GitOps configuration repo. This repo owns the application code and the build/test/scan/publish pipeline. It never touches a Kubernetes cluster.

**GitOps configuration repository:** [`gitops-k8s-config`](https://github.com/aniket-devop/gitops-k8s-config) — Helm chart, environment values, and the ArgoCD `Application` that deploys this app to a Kind cluster. Architecture diagrams, ArgoCD screenshots, and rollback evidence live there.

**At a glance**

| | |
|---|---|
| What I built | A FastAPI app and a GitHub Actions CI pipeline that tests, scans, and publishes it |
| What I own | Application code, tests, Dockerfile, and the full CI workflow, including the handoff into the GitOps repo |
| Where CI stops | A Git commit to `gitops-k8s-config` — no cluster access from this repo, ever |

## Key Architecture Boundary

```
Developer → gitops-demo-app → GitHub Actions → pytest → Docker build
   → Trivy CRITICAL scan → GHCR → Git commit to gitops-k8s-config
   → ArgoCD → Kind Kubernetes
```

**CI builds and publishes. Git records desired state. ArgoCD deploys and reconciles.**

**CI does not directly deploy to Kubernetes.** This repo's workflow stops at a Git commit to `gitops-k8s-config`. No `kubectl`, no Helm CLI, and no cluster credentials exist anywhere in this repo or its workflow. ArgoCD, running independently in the other repo's domain, is the only component with cluster access.

## Technology Stack

| Layer | Technology |
|---|---|
| Application | FastAPI, Python 3.12 |
| Testing | pytest, `fastapi.testclient.TestClient` |
| Container | Docker, `python:3.12-alpine`, non-root `appuser` |
| CI | GitHub Actions |
| Security scanning | Trivy (CRITICAL severity gate) |
| Registry | GitHub Container Registry (GHCR) |
| Deployment (other repo) | Helm, ArgoCD, Kind |

**Pinned dependencies** (`requirements.txt`): `fastapi==0.115.0`, `uvicorn[standard]==0.30.6`, `pytest==8.3.3`, `httpx==0.27.2`

## Two-Repository Architecture

| Repo | Owns | Role |
|---|---|---|
| `gitops-demo-app` (this repo) | FastAPI source, tests, Dockerfile, CI workflow | Builds, tests, scans, and publishes a container image |
| [`gitops-k8s-config`](https://github.com/aniket-devop/gitops-k8s-config) | Helm chart, environment values, ArgoCD `Application` | Desired cluster state — watched and reconciled by ArgoCD |

**Why split the repos:** it keeps cluster credentials out of the application codebase entirely. This repo's CI can build, test, scan, and publish an image, but has no way to change what's running in the cluster — that's a separate, auditable step owned by a different repo and a different credential (`GITOPS_REPO_TOKEN`).

## What This App Does

A minimal FastAPI service with three endpoints:

| Endpoint | Purpose | Example response |
|---|---|---|
| `GET /health` | Liveness/readiness check | `{"status": "ok"}` |
| `GET /version` | Current app version | `{"version": "2.0.0", "message": "..."}` |
| `GET /` | Service status | `{"service": "gitops-demo-app", "status": "running"}` |

The application logic is intentionally minimal — the focus of this project is the pipeline and the repo boundary around it, not the business logic of the service itself. `tests/test_main.py` covers all three endpoints with status codes and response bodies; `pytest` runs as the first gate in CI, so a broken commit never gets containerized or scanned.

`/health` backs the liveness and readiness probes configured on the deployment side (see `gitops-k8s-config`); `/version` makes it possible to confirm, from outside the cluster, exactly which build is currently running.

## CI Pipeline

![CI Pipeline Diagram](images/ci-pipeline-diagram.png)

On every push to `main`, `.github/workflows/ci.yml` runs:

```
checkout → pytest → derive commit-SHA image tag → docker build
   → Trivy CRITICAL scan → push to GHCR → update dev tag in gitops-k8s-config
```

| Step | Action | Failure behavior |
|---|---|---|
| 1 | Checkout, set up Python 3.12, install `requirements.txt` | — |
| 2 | Run `pytest` | Failing test blocks everything downstream |
| 3 | Derive image tag from short commit SHA | Every published image traces back to an exact commit |
| 4 | Build the Docker image | — |
| 5 | Scan with Trivy (`severity: CRITICAL`, `exit-code: "1"`) | CRITICAL finding fails the job before the image reaches GHCR |
| 6 | Push to GHCR (`ghcr.io/aniket-devop/gitops-demo`) | Only reached if the scan passes |
| 7 | Clone `gitops-k8s-config` with `GITOPS_REPO_TOKEN`, update `environments/dev/values-dev.yaml`, commit as `github-actions[bot]`, push | — |

Step 7 is a plain Git commit to another repository — nothing more. ArgoCD picks up that change on its own watch cycle; reconciliation itself is documented in the [`gitops-k8s-config` README](https://github.com/aniket-devop/gitops-k8s-config).

**Why commit-SHA tags:** every published image maps back to an exact source commit — no ambiguous `latest` tag.

**Why GHCR:** already authenticated through the existing `GITHUB_TOKEN`, so there's no separate registry account to manage.

**Why Trivy is a hard gate:** a single Action step (`exit-code: "1"`) that fails the job outright on a CRITICAL finding, rather than producing an informational report someone has to act on later.

**Why CRITICAL-only gating:** it stops anything severe from reaching GHCR without blocking the pipeline on HIGH/MEDIUM findings that don't represent immediate risk — a deliberate tradeoff for this project's scope, not a claim that lower severities don't matter.

**Why CI stops at Git:** the workflow's last step is a commit, not a deploy — cluster access is deliberately kept out of this repo and its credentials.

**Why ArgoCD owns deployment:** a single component with cluster credentials, running its own reconciliation loop, is a smaller and more auditable attack surface than letting every CI run authenticate against the cluster directly. That tradeoff is made explicit in [`gitops-k8s-config`](https://github.com/aniket-devop/gitops-k8s-config), where ArgoCD's sync policy lives.

## Security

- **Non-root container** — the Dockerfile creates and switches to an unprivileged user (`adduser -D appuser && chown -R appuser:appuser /app`, `USER appuser`) before the app runs
- **Minimal base image** — `python:3.12-alpine`
- **Trivy CRITICAL gate** — hard-fails (`exit-code: "1"`) before any image reaches GHCR
- **Separated credentials** — GHCR auth uses `GITHUB_TOKEN`; the cross-repo commit to `gitops-k8s-config` uses a distinct, separately scoped `GITOPS_REPO_TOKEN`

Not implemented in this repo: image signing, SAST or dependency scanning beyond the Trivy image scan, and branch-protection or PR-gated checks ahead of `main`.

### Engineering Judgment

- **Non-root by default:** running as `appuser` limits blast radius if the container is ever compromised — a small, cheap control relative to the risk it removes.
- **Scan before push, not after:** Trivy runs against the built image before it ever reaches GHCR, so a CRITICAL finding is a build failure, not a published artifact that has to be pulled back.
- **Two credentials, two blast radii:** `GITHUB_TOKEN` can push to GHCR; `GITOPS_REPO_TOKEN` can commit to the config repo. Neither can touch the cluster, and compromising one doesn't hand over the other.

## Repository Structure

```
gitops-demo-app/
├── .github/workflows/     # ci.yml — the pipeline described above
├── app/                   # FastAPI source
├── tests/                 # pytest suite covering all three endpoints
├── images/                # CI pipeline diagram and run evidence
├── Dockerfile
├── requirements.txt
├── .dockerignore
└── .gitignore
```

## Validation / Evidence

- CI workflow (`.github/workflows/ci.yml`) enforces test → scan → push, in that order, with the scan step able to block the push on a CRITICAL finding
- Published image tags in GHCR are short commit SHAs, directly traceable to commits in this repo
- The image tag committed to `gitops-k8s-config`'s `environments/dev/values-dev.yaml` matches this repo's corresponding commit SHA
- Full deployment reconciliation — ArgoCD picking up that commit and syncing the cluster — is evidenced separately in `gitops-k8s-config`, since this repo has no visibility into the cluster itself

![CI Pipeline Result](images/ci-run-summary.png)

![CI Pipeline Evidence](images/ci-run-evidence.png)

A real GitHub Actions run for this workflow — every step, from test through Trivy scan, GHCR push, and the GitOps repo update, completing successfully.

Deployment behavior, ArgoCD sync status, and rollback evidence are validated and documented in [`gitops-k8s-config`](https://github.com/aniket-devop/gitops-k8s-config) — not duplicated here.

## Limitations

- CI updates only the `dev` environment's image tag; `staging` exists in `gitops-k8s-config` but is not part of the automated promotion path
- This repository does not deploy to Kubernetes under any circumstance — deployment is entirely ArgoCD's responsibility, in the other repo
- No image signing or SAST/dependency scanning beyond the Trivy CRITICAL image scan
- No PR-based checks — the pipeline runs on push to `main`, not on pull requests
- This is a local Kind cluster demonstration, not a production or cloud Kubernetes deployment

## Running Locally

**Prerequisites:** Python 3.12, or Docker.

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or via Docker:

```bash
docker build -t gitops-demo .
docker run -p 8000:8000 gitops-demo
```

Verify it's up:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## GitOps Configuration Repository

This repo builds and publishes an image; it does not decide what runs in the cluster. For the Helm chart, ArgoCD `Application`, environment values, architecture diagram, and deployment/rollback evidence, see [`gitops-k8s-config`](https://github.com/aniket-devop/gitops-k8s-config).
