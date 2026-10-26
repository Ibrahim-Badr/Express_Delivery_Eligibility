# Express Delivery Eligibility (`eligibilite-livraison-express`)

Production-ready Machine Learning application and REST API that predicts whether an e-commerce order is eligible for express delivery (`oui` / `non`) based on quantitative and categorical order features.

---

## 1. Architecture Overview

This project transforms an experimental Jupyter Notebook into a modular, maintainable application following **Clean Architecture** and **SOLID / DRY / YAGNI** principles:

- **Separation of Training & Serving**: Model training is executed as an offline CLI job (`python -m src.cli train`), never via an HTTP endpoint. The FastAPI server loads the serialized model artifact once and serves low-latency predictions.
- **Dependency Inversion (Ports & Adapters)**: High-level application logic (`api/`, `ml/`) depends solely on abstract contracts (`OrderStore`, `ModelRepository`, `PredictionStore`) defined in `src/infra/abstractions/`. Concrete adapters (`MemoryOrderStore`, `FileModelRepository`, `MemoryPredictionStore`, `PostgresPredictionStore`) are wired in `src/core/dependencies.py`.
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
│   ├── pipeline.pkl                        # Legacy-compatible pipeline artifact
│   ├── model_card.json                     # Full model metadata and evaluation metrics
│   ├── metrics.json                        # Accuracy, Precision, Recall, F1, ROC AUC
│   └── features.json                       # Ordered list of model features
├── data/                                   # Local dataset directory
│   └── raw_orders.csv                      # Synthetic orders dataset
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
│       └── 0003-securite-entrees-sorties-et-donnees.md
├── notebooks/
│   └── project_test_v1_final_final2.ipynb  # Original experimental notebook
├── src/
│   ├── __init__.py
│   ├── main.py                             # FastAPI application entrypoint & router registration
│   ├── cli.py                              # CLI entrypoint (train, serve, predict, generate-data)
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
│   │   ├── cleaning.py                     # validate_dataset() and clean_orders_data()
│   │   └── features.py                     # orders_to_dataframe() and scikit-learn ColumnTransformer
│   ├── ml/                                 # Machine Learning pipeline, training, evaluation & inference
│   │   ├── __init__.py
│   │   ├── data_generation.py              # Reproducible synthetic order generator
│   │   ├── pipeline.py                     # MLPipeline (Imputer + StandardScaler/OneHot + LogisticRegression)
│   │   ├── training.py                     # TrainTestSplitter, MLTrainer (with MLflow logging) & train()
│   │   ├── evaluation.py                   # Classification metrics & ModelCard builder
│   │   └── predictor.py                    # MLPredict service with configurable decision threshold
│   ├── infra/                              # Infrastructure layer (Ports & Adapters)
│   │   ├── __init__.py
│   │   ├── abstractions/                   # Abstract interfaces (Ports)
│   │   │   ├── model_repository.py         # ModelRepository ABC
│   │   │   ├── order_store.py              # OrderStore ABC
│   │   │   └── prediction_store.py         # PredictionStore ABC
│   │   ├── local/                          # Local / In-memory implementations (Dev & Test adapters)
│   │   │   ├── file_model_repository.py    # Local filesystem joblib & JSON model repository
│   │   │   ├── memory_order_store.py       # In-memory order store & training data loader
│   │   │   └── memory_prediction_store.py  # In-memory prediction store
│   │   └── database/                       # SQL database implementations (Prod adapter)
│   │       ├── database.py                 # SQLAlchemy engine & session factory
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
├── tests/                                  # Automated Pytest suite
│   ├── conftest.py                         # Shared fixtures, FakePipeline & FakeModelRepository
│   ├── etl/
│   │   └── test_cleaning.py                # Unit tests for dataset validation, cleaning & feature contract
│   ├── ml/
│   │   └── test_ml.py                      # Unit tests for MLPredict thresholds, splitter & MLTrainer
│   ├── infra/
│   │   └── test_repositories.py            # Contract tests for OrderStore, PredictionStore & FileModelRepository
│   └── api/
│       └── test_api.py                     # FastAPI endpoint tests (200, 202, 422, 503)
├── .dockerignore                           # Excludes non-production files from Docker build context
├── .env.example                            # Example environment variables template
├── Dockerfile                              # Hardened 2-stage production container image (non-root user)
├── docker-compose.yml                      # Multi-container local setup (FastAPI + PostgreSQL 15)
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

## 5. Running with Docker & PostgreSQL

The [`docker-compose.yml`](docker-compose.yml) orchestrates **3 separated containers** following the MLOps principle of separating Training from Serving:

1. **`express_delivery_db` (`db`)**: Stateful PostgreSQL 15 database (`localhost:5432`) with persistent volume `postgres_data`.
2. **`express_delivery_trainer` (`trainer`)**: One-shot ML batch job (`python -m src.cli train`) that generates/cleans data, trains the pipeline, writes model artifacts to the shared `model_artifacts` volume, and exits cleanly.
3. **`express_delivery_api` (`api`)**: Stateless FastAPI server (`http://localhost:8000`) that starts only after `db` is healthy and `trainer` completes (`service_completed_successfully`), mounting `model_artifacts` as read-only (`:ro`).

```bash
# Build and start all services
docker-compose up -d --build

# Re-run the ML training job on demand without rebuilding
docker-compose run --rm trainer
```

---

## 6. Testing & Code Quality

```bash
# Run unit, contract, and API tests
pytest -v

# Run Ruff linter
ruff check .
```

---

## 7. Architecture Decision Records (ADRs)

- [ADR 0001 - Deployment Platform Choice (Azure Hybrid IaaS/PaaS)](docs/adr/0001-choix-plateforme-de-deploiement.md)
- [ADR 0002 - Deployment Strategy & Environments (Terraform + GitHub Actions)](docs/adr/0002-strategie-de-deploiement.md)
- [ADR 0003 - I/O Validation & Data Access Security (Pydantic + Azure Key Vault)](docs/adr/0003-securite-entrees-sorties-et-donnees.md)
