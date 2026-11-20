# ADR 0002: Model Artifact Storage

## Context
In accordance with MLOps separation of concerns, model **training** is executed as an independent batch/orchestration process (`trainer` and the **Apache Airflow** `express_delivery_retraining` DAG), while model **serving** is handled by a stateless FastAPI `api` service. We need a reliable way to version, share, and reload trained scikit-learn pipelines and metadata between these services without corrupting concurrent reads.

## Decision
We define the `ModelRepository` port in `src/infra/abstractions/model_repository.py` and implement a filesystem-based repository (`FileModelRepository` in `src/infra/local/file_model_repository.py`) paired with MLflow experiment tracking:
1. **Model Artifacts (`artifacts/`)**:
   * `express_delivery_model.joblib`: Serialized scikit-learn `Pipeline` (preprocessing + `LogisticRegression`).
   * `model_card.json`: Full model governance metadata, evaluation metrics, and timestamps.
   * `metrics.json` & `features.json`: Structured metrics and ordered `FEATURE_COLUMNS` contract.
2. **Atomic Publishing & Hot-Reload**: `FileModelRepository.save()` writes each artifact to a sibling temporary file in the same volume, applies `0o664` group permissions, and swaps it atomically via `os.replace()` — publishing `express_delivery_model.joblib` first and `model_card.json` last. In Docker Compose (`docker-compose.test.yml` and `docker-compose.prod.yml`), the shared Docker volume (`test_model_artifacts` / `prod_model_artifacts`) is mounted read-write on `trainer` / `airflow` and read-only (`:ro`) on `api`. `FileModelRepository` tracks file modification timestamps (`st_mtime`) so the `api` container hot-reloads newly promoted models automatically without partial reads or restarts.
3. **Experiment Tracking**: Training metrics and parameters are logged via MLflow to `local_databases/mlflow.db`.

## Consequences
* **Positive**:
  * Zero external object-storage dependency required for single-host Docker Compose deployments.
  * Atomic Champion vs. Challenger promotion: `RetrainingOrchestrator` writes to `ModelRepository` only after a candidate passes quality floors and beats/matches the active champion on the same test split.
  * Zero-downtime model updates in the FastAPI container via `st_mtime` hot-reloading.
* **Negative**:
  * Local filesystem/volume storage assumes training and API containers run on the same host (or share a network filesystem).

## Future Migration Triggers
Introduce a remote registry adapter (`MlflowModelRepository` or Azure Blob Storage) implementing `ModelRepository` when scaling API replicas across multiple independent cloud nodes.
