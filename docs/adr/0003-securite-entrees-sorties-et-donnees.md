# ADR 0003: Input/Output Validation and Data Access Security

## Context
The REST API receives external HTTP requests to evaluate order eligibility and connects to a remote database (PostgreSQL on Azure). It is critical to prevent injection attacks, enforce strict input contracts, and protect database credentials.

## Decision
We apply defense-in-depth across two layers:

### 1. Input and Output Security
* Use **FastAPI** coupled with **Pydantic** schemas (`OrderFeatures`, `Prediction`, `BatchPredictionRequest`).
* Every incoming JSON payload is strictly validated against type and domain constraints (e.g., `hour` between `0` and `23`, `carrier_capacity` between `0.0` and `1.0`, `extra="forbid"`). Invalid requests are immediately rejected with `HTTP 422 Unprocessable Entity` before reaching the business logic or ML pipeline.

### 2. Data Access Security
* **Zero secrets in source control**: Database connection strings (`DATABASE_URL`) and passwords are never committed to Git.
* **Azure Key Vault**: Production secrets and credentials are stored securely in Azure Key Vault and injected at runtime via environment variables or Managed Identities.

## Consequences
* **Positive**:
  * Strong protection against malformed payloads and injection attacks before model inference.
  * Eliminates the risk of credential leaks in public GitHub repositories.
* **Negative**:
  * Requires configuring access policies / Managed Identities between the Azure VM, GitHub Actions, and Azure Key Vault.
