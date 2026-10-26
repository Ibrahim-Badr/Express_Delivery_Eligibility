# Security Policy

## 1. Supported Versions

The following versions of the Express Delivery Eligibility service are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
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
- **Zero Secrets in Git**: `.env`, `.env.dev`, `.env.test`, and `.env.prod` are excluded via `.gitignore`. Only `.env.example` with non-sensitive placeholders is committed.
- **Cloud Secret Storage**: Production database credentials (`DATABASE_URL`) and API secrets are stored in **Azure Key Vault** and injected at runtime.

### Container Security
- The production Docker image uses a **multi-stage build** (`python:3.11-slim`) that strips compilers (`gcc`) and build-time headers from the final image.
- The container runs as an unprivileged **non-root user** (`appuser`, UID `10001`) with `no-new-privileges:true` enforced in `docker-compose.yml`.
- Every release image is automatically scanned for `CRITICAL` and `HIGH` OS and Python package CVEs using **Aqua Security Trivy** (`aquasecurity/trivy-action`) in the GitHub Actions release pipeline before being published to `ghcr.io`.
