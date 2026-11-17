# ADR 0005: Deployment Strategy and Environments

## Context
The application progresses across three distinct lifecycle stages (`Dev`, `Test`, and `Prod`). In addition, MLOps best practices require strictly separating **application build/CI/CD** (code quality, tests, Docker image packaging) from **ML runtime execution** (database ingestion, training, and retraining).

## Decision
We implement a **GitFlow + IaC + GitHub Actions CI/CD + Dual Docker Compose** strategy:
1. **GitFlow Branching**:
   * `feature/*` branches merge into `develop` (Dev integration).
   * `release/*` branches stabilize candidates for Test validation before merging into `main` (Prod) and tagging (`vX.Y.Z`).
   * `hotfix/*` branches patch critical `main` defects and merge back into both `main` and `develop`.
2. **Continuous Integration (`.github/workflows/ci.yml`)**:
   * Runs `ruff check .`, `pylint src/`, and `pytest -v` on pushes and PRs without connecting to production databases or training ML models at CI/build time.
3. **Continuous Delivery (`.github/workflows/release-docker.yml`)**:
   * On GitHub release or `v*.*.*` tag, builds the hardened 2-stage production `Dockerfile` (without baked-in training artifacts), scans it with **Aqua Trivy**, and pushes to **GHCR (`ghcr.io`)**.
4. **Infrastructure & Runtime Environments**:
   * **Infrastructure as Code (Terraform)** provisions Azure resources deterministically (`terraform apply` / `terraform destroy`).
   * **Test Stack (`docker-compose.test.yml`)**: Runs `db` (port `5433`), bounded `erp-simulator`, `trainer`, and containerized `test-runner`.
   * **Production Stack (`docker-compose.prod.yml`)**: Runs `db` (port `5432`), continuous `erp-simulator`, initial `trainer`, `api` (FastAPI), and `orchestrator` (`RetrainingOrchestrator` with dynamic hybrid trigger and Champion vs. Challenger validation).

## Consequences
* **Positive**:
  * Clear separation between build-time artifacts (stateless Python app image) and runtime state (database records and promoted `.joblib` models).
  * Reproducible environment promotion and one-command teardown to protect cloud budgets.
* **Negative**:
  * Requires maintaining synchronization across GitHub Actions workflows, Terraform configurations, and Compose files.
