# Express Delivery Eligibility (`eligibilite-livraison-express`)

Production-ready Machine Learning application and REST API that predicts whether an e-commerce order is eligible for express delivery (`oui` / `non`) based on quantitative and categorical order features.

---

## 1. Architecture Overview

This project transforms an experimental Jupyter Notebook into a modular, maintainable application following **Clean Architecture** and **SOLID / DRY / YAGNI** principles:

- **Separation of Training & Serving**: Model training is executed as an independent execution process (`python -m src.cli train` or `orchestrator` daemon), never during image build or via an HTTP endpoint. The FastAPI server loads the serialized model artifact and serves low-latency predictions.
- **Dependency Inversion (Ports & Adapters)**: High-level application logic (`api/`, `ml/`, `orchestration/`) depends solely on abstract contracts (`OrderRepository`, `ModelRepository`, `PredictionStore`) defined in `src/infra/abstractions/`. Concrete adapters (`PostgresOrderRepository`, `MemoryOrderStore`, `FileModelRepository`, `MemoryPredictionStore`, `PostgresPredictionStore`) are wired in `src/core/dependencies.py`.
- **Single Feature Contract**: `FEATURE_COLUMNS` in `src/core/constants.py` and `orders_to_dataframe()` in `src/etl/features.py` guarantee identical column ordering between training and inference.

---

## 2. Project Structure

```text
Express_Delivery_Eligibility/
├── .github/
│   └── workflows/                          # Automated CI/CD pipelines (GitHub Actions)
│       ├── ci.yml                          # Linting (Ruff + Pylint) & automated tests (Pytest)
│       └── release-docker.yml              # Automated Docker build, compression & push to GHCR on release
├── artifacts/                              # Generated model artifacts (created by train job)
│   ├── express_delivery_model.joblib       # Trained scikit-learn Pipeline (preprocessor + classifier)
│   ├── model_card.json                     # Full model metadata and evaluation metrics
│   ├── metrics.json                        # Accuracy, Precision, Recall, F1, ROC AUC
│   └── features.json                       # Ordered list of model features
├── data/                                   # Local dataset directory
│   └── raw_orders.csv                      # Synthetic orders dataset
├── erp/                                    # Self-contained ERP Simulator ("ERP Pro 2015")
│   ├── Dockerfile                          # Container definition for the ERP order generator
│   ├── requirements.txt                    # Simulator dependencies (psycopg[binary])
│   ├── config.py                           # Simulator environment settings
│   ├── erp_simulator.py                    # Main simulator entrypoint (historical + live stream)
│   ├── generator.py                        # Order generation with legacy 2015/2017 schema shifts
│   ├── simulator.py                        # Batching and orchestration logic
│   └── storage.py                          # PostgreSQL writer and schema migrations
├── local_databases/                        # Local SQLite runtime databases (ignored by Git)
│   ├── .gitkeep
│   ├── local.db                            # Local application state (orders & prediction records)
│   └── mlflow.db                           # Local MLflow experiment tracking & metrics database
├── docs/                                   # Collaboration, security & architectural documentation
│   ├── CONTRIBUTING.md                     # GitFlow workflow, coding standards & PR guidelines
│   ├── SECURITY.md                         # Security policy, vulnerability reporting & hardening practices
│   ├── CODE_OF_CONDUCT.md                  # Contributor Covenant Code of Conduct
│   └── adr/                                # Architecture Decision Records (ADRs)
│       ├── 0001-choix-plateforme-de-deploiement.md
│       ├── 0002-strategie-de-deploiement.md
│       ├── 0003-securite-entrees-sorties-et-donnees.md
│       └── 0004-choix-base-de-donnees-source-commandes.md
├── notebooks/
│   └── project_test_v1_final_final2.ipynb  # Original experimental notebook
├── src/
│   ├── __init__.py
│   ├── main.py                             # FastAPI application entrypoint & router registration
│   ├── cli.py                              # CLI entrypoint (train, serve, predict, retrain-daemon)
│   ├── domain/                             # Core business entities (framework-independent)
│   │   ├── __init__.py
│   │   └── entities.py                     # Immutable dataclasses: OrderEntity, PredictionEntity, ModelEntity
│   ├── core/                               # Configuration, Dependency Injection & Cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── config.py                       # Pydantic Settings loaded from environment / .env
│   │   ├── constants.py                    # Single source of truth for FEATURE_COLUMNS
│   │   ├── dependencies.py                 # Composition root for FastAPI Depends()
│   │   ├── errors.py                       # Custom domain exceptions
│   │   └── logging.py                      # Application logging setup
│   ├── etl/                                # Data validation, cleaning & feature engineering
│   │   ├── __init__.py
│   │   ├── cleaning.py                     # validate_dataset(), clean_orders_data() & ERP imputation
│   │   └── features.py                     # orders_to_dataframe(), dataframe_to_training_entities() & ColumnTransformer
│   ├── ml/                                 # Machine Learning pipeline, training, evaluation & inference
│   │   ├── __init__.py
│   │   ├── data_generation.py              # Reproducible synthetic order generator
│   │   ├── pipeline.py                     # MLPipeline (Imputer + StandardScaler/OneHot + LogisticRegression)
│   │   ├── training.py                     # TrainTestSplitter, MLTrainer (with MLflow logging) & train()
│   │   ├── evaluation.py                   # Classification metrics computation
│   │   └── predictor.py                    # MLPredict service with configurable decision threshold
│   ├── orchestration/                      # MLOps Continuous Retraining Orchestrator
│   │   ├── __init__.py
│   │   └── retraining.py                   # RetrainingOrchestrator daemon & candidate validation
│   ├── infra/                              # Infrastructure layer (Ports & Adapters)
│   │   ├── __init__.py
│   │   ├── abstractions/                   # Abstract interfaces (Ports)
│   │   │   ├── model_repository.py         # ModelRepository ABC
│   │   │   ├── order_repository.py         # OrderRepository ABC
│   │   │   └── prediction_store.py         # PredictionStore ABC
│   │   ├── local/                          # Local / In-memory implementations (Dev & Test adapters)
│   │   │   ├── file_model_repository.py    # Local filesystem joblib & JSON model repository
│   │   │   ├── memory_order_store.py       # InMemoryOrderRepository / MemoryOrderStore
│   │   │   └── memory_prediction_store.py  # In-memory prediction store
│   │   └── database/                       # SQL database implementations (Prod adapter)
│   │       ├── database.py                 # SQLAlchemy engine & session factory
│   │       ├── postgres_order_repository.py# PostgreSQL OrderRepository adapter for ERP orders
│   │       └── postgres_prediction_store.py# PostgreSQL / SQLAlchemy prediction store
│   └── api/                                # HTTP Presentation layer (FastAPI)
│       ├── __init__.py
│       ├── error_handlers.py               # Exception to HTTP status code mappings (404, 422, 503)
│       ├── schemas/                        # Pydantic request/response schemas (OpenAPI contract)
│       │   └── __init__.py
│       └── routers/                        # Versioned route handlers
│           ├── health.py                   # GET /health & GET /health/ready
│           ├── orders.py                   # POST /v1/orders & GET /v1/orders/{order_id}
│           ├── predictions.py              # POST /v1/predictions, /batch, GET /v1/predictions/{order_id}
│           └── model.py                    # GET /v1/model
├── tests/                                  # Automated Pytest suite (20 tests)
│   ├── conftest.py                         # Shared fixtures, FakePipeline & FakeModelRepository
│   ├── etl/
│   │   └── test_cleaning.py                # Unit tests for dataset validation, cleaning & feature contract
│   ├── ml/
│   │   └── test_ml.py                      # Unit tests for MLPredict thresholds, splitter & MLTrainer
│   ├── orchestration/
│   │   └── test_retraining.py              # Unit tests for RetrainingOrchestrator promotion & rejection
│   ├── infra/
│   │   └── test_repositories.py            # Contract tests for OrderRepository, PredictionStore & FileModelRepository
│   └── api/
│       └── test_api.py                     # FastAPI endpoint tests (200, 202, 422, 503)
├── .dockerignore                           # Excludes non-production files from Docker build context
├── .env.example                            # Example environment variables template
├── Dockerfile                              # Hardened 2-stage production container image (non-root user)
├── docker-compose.test.yml                 # Automated containerized test environment (Postgres + ERP + Trainer + Pytest)
├── docker-compose.prod.yml                 # Production environment (Postgres + ERP + Trainer + FastAPI + Orchestrator)
├── LICENSE                                 # MIT License
├── openapi.yml                             # OpenAPI 3.1 specification contract
├── order.json                              # Sample order payload for CLI and HTTP testing
├── pyproject.toml                          # Package metadata, Pytest, Ruff & Pylint configuration
├── requirements.txt                        # Full development & CI dependencies
└── requirements-prod.txt                   # Lightweight production runtime dependencies
```

---

## 3. Quickstart & Usage

### Local Installation

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### CLI Commands

```bash
# 1. Train the model (automatically generates & cleans data if missing, logs to MLflow, writes artifacts/)
python -m src.cli train

# 2. Predict eligibility for a single order JSON file locally (without starting the HTTP server)
python -m src.cli predict --file order.json

# 3. Start the FastAPI server (default: http://127.0.0.1:8000)
python -m src.cli serve --host 127.0.0.1 --port 8000

# 4. (Optional) Explicitly regenerate the raw synthetic dataset
python -m src.cli generate-data --n-rows 6000 --random-state 42
```

---

## 4. REST API Endpoints

Once the server is running (`python -m src.cli serve`), interactive documentation is available at `http://127.0.0.1:8000/docs`.

| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness probe (process is alive) | `200` |
| `GET` | `/health/ready` | Readiness probe (checks if ML model is loaded) | `200`, `503` |
| `POST` | `/predict` | Predict single order eligibility (lite alias) | `200`, `422`, `503` |
| `POST` | `/v1/predictions` | Predict single order eligibility and persist result | `200`, `422`, `503` |
| `POST` | `/v1/predictions/batch` | Predict batch of orders (up to 1000) | `200`, `422`, `503` |
| `GET` | `/v1/predictions/{order_id}` | Retrieve a previously computed prediction | `200`, `404` |
| `POST` | `/v1/orders` | Submit an order for asynchronous processing | `202`, `422` |
| `GET` | `/v1/orders/{order_id}` | Retrieve stored order features | `200`, `404` |
| `GET` | `/v1/model` | Retrieve active model card metadata and metrics | `200`, `503` |

---

## 5. Running with Docker & PostgreSQL (Test & Prod Environments)

Following the project requirements, two dedicated Docker Compose environments are provided:

### A. Test Environment (`docker-compose.test.yml`)
The test environment runs against a lightweight, bounded test database (`port 5433:5432`) to validate ERP data ingestion, model training, and automated test execution inside containers:

```bash
# Start the test environment (Postgres, bounded ERP simulator, Trainer, and automated Test Runner)
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Teardown and reset test volumes
docker compose -f docker-compose.test.yml down -v
```

Services orchestrated:
1. **`db` (`postgres:17-alpine`)**: Test database `livraison_express` on port `5433`.
2. **`erp-simulator`**: Populates bounded historical orders (100 orders) and a small live stream.
3. **`trainer`**: Trains the model on the newly ingested PostgreSQL data and exports artifacts.
4. **`test-runner`**: Runs the complete `pytest` test suite against the live test database.

---

### B. Production Environment (`docker-compose.prod.yml`)
The production environment operates 24/7 with the full ERP live stream, model inference API, and continuous retraining orchestrator:

```bash
# Build and launch production stack in detached mode
docker compose -f docker-compose.prod.yml up -d --build

# View logs from all services (or specifically erp-simulator / orchestrator)
docker compose -f docker-compose.prod.yml logs -f erp-simulator
docker compose -f docker-compose.prod.yml logs -f orchestrator

# Stop production stack
docker compose -f docker-compose.prod.yml down
```

Services orchestrated:
1. **`db` (`postgres:17-alpine`)**: Stateful production ERP database on port `5432` with persistent volume `prod_postgres_data`.
2. **`erp-simulator`**: Enterprise ERP simulator (`ERP Pro 2015`) continuously publishing batches of 5 orders every 5 seconds.
3. **`trainer`**: Initial training batch job that prepares model artifacts before API launch.
4. **`api` (`FastAPI`)**: Stateless prediction API running as non-root `appuser` on port `8000`.
5. **`orchestrator`**: Continuous background daemon monitoring PostgreSQL order growth, triggering automated retraining when 50+ new orders arrive, and validating model performance (ROC-AUC $\ge 0.70$) before promoting artifacts.

---

## 6. Complete Local Testing Guide (All Layers)

### Layer 1: Automated Unit & Contract Tests (Pytest)
Run all 18 automated unit, contract, and integration tests:
```bash
python -m pytest -v
```

Run specific test modules:
```bash
# Infrastructure and Repository contracts (PostgresOrderRepository, MemoryOrderStore, ModelRepository)
python -m pytest tests/infra/test_repositories.py -v

# ETL pipeline, data cleaning, legacy schema migration imputation, category harmonization
python -m pytest tests/etl/test_cleaning.py -v

# ML training, train/test stratified splitter, decision thresholds, and MLflow logging
python -m pytest tests/ml/test_ml.py -v

# FastAPI REST API endpoints, liveness/readiness probes, and 422/503 exception handlers
python -m pytest tests/api/test_api.py -v
```

### Layer 2: Machine Learning Training (CLI)
Execute the complete data loading, ETL cleaning, model fitting, and artifact export pipeline:
```bash
python -m src.cli train
```
* **Inputs**: Historical order stream from `PostgresOrderRepository` (or local dataset generator fallback).
* **Outputs**: Production artifacts saved in `artifacts/` (`express_delivery_model.joblib`, `metrics.json`, `features.json`, `model_card.json`) and run metrics tracked in MLflow.

### Layer 3: Offline Model Prediction (CLI)
Evaluate eligibility directly from a JSON order payload without running the web server:
```bash
python -m src.cli predict --file order.json
```
Output:
```json
{
  "express_eligible": true,
  "decision": "oui",
  "probability": 0.9376,
  "model_version": "1.0.0",
  "prediction_timestamp": "...",
  "order_id": null,
  "latency_ms": null
}
```

### Layer 4: Running the Live FastAPI REST API Server
Start the local development server with auto-reload:
```bash
python -m uvicorn src.main:app --reload --port 8000
# Or via CLI helper:
python -m src.cli serve --host 127.0.0.1 --port 8000
```
* **Interactive OpenAPI Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Layer 5: Testing API Endpoints via PowerShell or cURL
In a second terminal, execute HTTP requests against the running service:

#### A. Health and Readiness Checks
```powershell
# Liveness probe (HTTP 200)
Invoke-RestMethod -Uri http://127.0.0.1:8000/health -Method GET

# Readiness probe (HTTP 200 when model is loaded, HTTP 503 if unavailable)
Invoke-RestMethod -Uri http://127.0.0.1:8000/health/ready -Method GET
```

#### B. Synchronous Model Inference (`/predict` & `/v1/predictions`)
```powershell
# Root alias prediction
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict `
  -Method POST `
  -ContentType "application/json" `
  -InFile order.json

# Versioned prediction with storage persistence
Invoke-RestMethod -Uri http://127.0.0.1:8000/v1/predictions `
  -Method POST `
  -ContentType "application/json" `
  -InFile order.json
```

#### C. Asynchronous Order Submission (`/v1/orders`)
```powershell
# Post order for asynchronous background processing (HTTP 202 Accepted)
Invoke-RestMethod -Uri http://127.0.0.1:8000/v1/orders `
  -Method POST `
  -ContentType "application/json" `
  -InFile order.json
```

#### D. Model Card & Governance Metadata (`/v1/model`)
```powershell
# Retrieve active model card, performance metrics, and governance limitations
Invoke-RestMethod -Uri http://127.0.0.1:8000/v1/model -Method GET
```

### Layer 6: MLflow Experiment Tracking Dashboard
To visualize model runs, ROC-AUC metrics, and hyperparameter comparisons in the browser:
```bash
# Note: Use 'python -m mlflow' to bypass Windows launcher path issues
python -m mlflow ui --backend-store-uri sqlite:///./local_databases/mlflow.db --port 5000
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) to view experiment metrics and artifacts.

---

## 7. Architecture Decision Records (ADRs)

- [ADR 0001 - Deployment Platform Choice (Azure Hybrid IaaS/PaaS)](docs/adr/0001-choix-plateforme-de-deploiement.md)
- [ADR 0002 - Deployment Strategy & Environments (Terraform + GitHub Actions)](docs/adr/0002-strategie-de-deploiement.md)
- [ADR 0003 - I/O Validation & Data Access Security (Pydantic + Azure Key Vault)](docs/adr/0003-securite-entrees-sorties-et-donnees.md)
- [ADR 0004 - Data Source Database Selection (PostgreSQL vs. MongoDB)](docs/adr/0004-choix-base-de-donnees-source-commandes.md)
