# ADR 0002: Deployment Strategy and Environment Management

## Context
The application must progress through three isolated environments (`Dev`, `Test`, and `Prod`). We need a reliable strategy to provision cloud infrastructure and deploy application updates automatically without error-prone manual steps.

## Decision
We adopt **Infrastructure as Code (IaC)** combined with **Continuous Integration and Continuous Deployment (CI/CD)**:
1. **Infrastructure (IaC)**: Use **Terraform** to create, update, and destroy Azure resources deterministically with a single command (`terraform apply` / `terraform destroy`).
2. **CI/CD**: Use **GitHub Actions** to automate linting (`ruff`), testing (`pytest`), Docker image builds, and deployment.
3. **Branching Strategy**:
   * The `develop` branch deploys to the **Dev** environment.
   * The `release` branch deploys to the **Test** environment.
   * The `main` branch deploys to the **Prod** environment.

## Consequences
* **Positive**:
  * 100% reproducible infrastructure and deployments.
  * Automated quality gates before any code reaches production.
  * Student budget protection through one-command teardown (`terraform destroy`).
* **Negative**:
  * Initial setup overhead for Terraform state and GitHub Actions secrets/environments.
