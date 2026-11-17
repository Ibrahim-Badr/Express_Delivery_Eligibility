# ADR 0004: Cloud, On-Premise, or Local?

## Context
We must decide where each stage of the application lifecycle executes—comparing **Local execution**, **On-Premise infrastructure**, and **Public Cloud (Microsoft Azure)**—while accounting for developer velocity, offline testability, network availability, and budget constraints.

## Decision
We adopt a **Cloud-first Production + Local-first Development** model:
1. **Production Environment — Public Cloud (Microsoft Azure)**:
   * Provides public HTTPS/API exposure, managed PostgreSQL backups, Azure Key Vault secret management, and reproducible infrastructure provisioning without purchasing or maintaining physical on-premise hardware.
2. **Development & Automated Test Environments — Local / Ephemeral Containers**:
   * **Fast Local Mode**: Developers run `src/cli.py` and `pytest` directly in `.venv` using in-memory/SQLite adapters (`DATABASE_URL=sqlite:///./local_databases/local.db`) with zero cloud cost or internet dependency.
   * **Isolated Integration Mode**: `docker-compose.test.yml` spins up a local containerized PostgreSQL (`port 5433`), bounded ERP simulator, trainer, and test runner on any workstation or CI runner.

## Consequences
* **Positive**:
  * Zero cloud expenditure during everyday coding, unit testing, and CI runs.
  * No physical server procurement, power, or network administration (eliminating on-premise maintenance).
  * Production deployment benefits from managed cloud SLA and security controls.
* **Negative**:
  * Cloud resources must be provisioned and torn down carefully (via Terraform) so student credits and monthly free hours are not exhausted by idle instances.
