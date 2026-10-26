# ADR 0001: Deployment Platform Choice

## Context
The Express Delivery Eligibility application needs to be deployed to production. We must choose between an On-Premise, Local, or Cloud hosting environment.
We have a strict student budget on Microsoft Azure ($88 credit) along with free 12-month tier allocations for several core services (notably 750 hours/month for a Linux VM and 750 hours/month for Azure Database for PostgreSQL).

## Decision
We decided to deploy the application on the **Cloud (Microsoft Azure)** using a hybrid IaaS / PaaS architecture:
1. **Compute (IaaS)**: An **Azure Linux VM (`B2ats v2`)** hosting the containerized FastAPI application via Docker.
2. **Database (PaaS)**: **Azure Database for PostgreSQL (Flexible Server)**. Instead of self-managing the database inside the VM, we delegate database administration (automated backups, patching, high availability) to Azure using the free `B1MS` burstable tier.

## Consequences
* **Positive**:
  * Zero monthly cost ($0) by staying within the free student tier quotas.
  * Cloud-native, scalable production architecture.
  * Clear separation of concerns between stateless compute (VM) and managed storage (PaaS).
* **Negative**:
  * Requires disciplined lifecycle management (via Terraform) to stop or destroy resources when not in use so free quotas are preserved.
