# ADR 0003: Deployment Platform Choice

## Context
The Express Delivery Eligibility platform consists of multiple cooperating services: PostgreSQL (`db`), RabbitMQ (`rabbitmq`), the ERP data simulator (`erp-simulator`), the initial training job (`trainer`), the FastAPI inference & Logistics Operator Dashboard service (`api`), and the Apache Airflow retraining orchestrator (`airflow`). We must select a compute and container platform under a strict student budget on Microsoft Azure ($88 credit and 12-month free tiers: 750 hours/month Linux VM and 750 hours/month Azure Database for PostgreSQL).

## Decision
We select **Docker & Docker Compose** running on a **Hybrid Azure IaaS / PaaS Platform**:
1. **Compute Platform (IaaS)**: An **Azure Linux VM (`B2ats v2`)** running Docker Engine and Docker Compose to host the containerized application image (`ghcr.io`), minimizing platform overhead and avoiding managed Kubernetes control-plane costs.
2. **Database Platform (PaaS)**: **Azure Database for PostgreSQL (Flexible Server, `B1MS` burstable tier)** so automated backups, OS patching, and security updates are handled by Azure rather than manually inside the VM.
3. **Container Registry**: **GitHub Container Registry (`ghcr.io`)** for hosting versioned, Trivy-scanned multi-stage Docker images built from `Dockerfile`.

## Consequences
* **Positive**:
  * Stays within Azure free-tier quotas ($0/month when managed properly).
  * Complete parity between local Docker Compose stacks (`docker-compose.prod.yml`) and the cloud VM runtime.
  * Avoids the operational complexity and RAM overhead of running an AKS (Kubernetes) cluster for a single-project workload.
* **Negative**:
  * Single-VM Docker Compose does not provide multi-node auto-scaling; migrating to Azure Container Apps or AKS would be required if high-availability horizontal cluster scaling is needed later.
