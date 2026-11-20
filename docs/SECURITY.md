# Security Policy

## 1. Supported Versions

The following versions of the Express Delivery Eligibility service are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## 2. Reporting a Vulnerability

If you discover a security vulnerability within this project, please **do not open a public GitHub issue**.

Instead, please report it privately by contacting the project maintainers with:
1. A description of the vulnerability and its potential impact.
2. Steps or a proof-of-concept payload to reproduce the issue.
3. Any suggested remediation or mitigation.

We will acknowledge receipt within **48 hours** and provide a remediation timeline after validating the report.

---

## 3. Application & Infrastructure Security Practices

### Input & Output Validation
- All incoming HTTP payloads are strictly validated using **Pydantic** schemas (`extra="forbid"`, numeric bounds, and strict `Literal` enumerations).
- Malformed requests are rejected with `HTTP 422 Unprocessable Entity` before reaching the Machine Learning pipeline or database layer.

### Secret & Credential Management
- **Zero Secrets in Git**: `.env` and environment-specific override files (`.env.*` except `.env.example`) are excluded via `.gitignore`. Only `.env.example` with non-sensitive placeholders is committed.
- **Cloud Secret Storage**: Production database credentials (`DATABASE_URL`) and API secrets are stored securely in **Azure Key Vault** and injected at runtime.

### Container & Network Security
- **Multi-Stage Minimal Images**: The production Docker image (`Dockerfile`) uses a 2-stage build (`python:3.11-slim`) that strips build compilers (`gcc`, `libpq-dev`), applies OS security upgrades (`apt-get upgrade`), and removes redundant system `pip`/`setuptools`/`wheel` metadata so images pass Aqua Trivy scans with zero `CRITICAL`/`HIGH` CVEs.
- **Non-Root Least Privilege**: Every custom service runs as a dedicated unprivileged user — `appuser` (UID/GID `10001`) for FastAPI/Trainer, `erpuser` (UID/GID `10002`) for `erp-simulator`, and `airflow` (with shared group `10001` for artifact volume access) for Apache Airflow — with `no-new-privileges:true` enforced in `docker-compose.prod.yml`.
- **Network Isolation**: PostgreSQL (`db`) is kept strictly on the internal Docker network with no host port exposure in production, while operational UIs (`airflow` on `127.0.0.1:8080`, `rabbitmq` management on `127.0.0.1:15672`) are bound exclusively to loopback.
- **Automated Vulnerability Scanning**: Every release image is scanned for `CRITICAL` and `HIGH` OS and Python package CVEs using **Aqua Security Trivy** (`aquasecurity/trivy-action`) in the GitHub Actions release pipeline before being published to `ghcr.io`.
