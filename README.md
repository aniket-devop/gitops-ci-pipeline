# \# gitops-demo-app

# 

# Application source repository for a GitOps-based Kubernetes deployment project.

# 

# This repo contains a minimal FastAPI application. On every push to `main`,

# GitHub Actions runs tests, builds a Docker image, scans it with Trivy,

# pushes it to GitHub Container Registry, and updates the image tag in the

# GitOps configuration repository. This repo never deploys directly to any

# cluster — deployment is handled entirely by ArgoCD, watching the separate

# config repo.

# 

# Full project documentation, architecture, and demos live in:

# 👉 \[gitops-k8s-config](https://github.com/aniket-devop/gitops-k8s-config)

# 

# \## Endpoints

# \- `GET /health` — liveness check

# \- `GET /version` — current app version

# \- `GET /` — service status

# 

# \## Tech

# FastAPI, pytest, Docker, GitHub Actions, Trivy

