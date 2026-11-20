# ADR 0001: Order Storage

## Context
The Express Delivery Eligibility application requires a structured mechanism to persist and query e-commerce orders across two distinct workflows:
1. **API Operations**: Accepting incoming orders via `POST /v1/orders`, retrieving order details via `GET /v1/orders/{order_id}`, and storing computed predictions (`PredictionStore`).
2. **ML Training & Retraining**: Reading historical and live order batches (`get_training_data()`, `count()`) to clean, validate, and train the classification model.

Following Clean Architecture and Dependency Inversion (Ports & Adapters), high-level modules (`src/api/`, `src/ml/`, `src/orchestration/`) must remain completely decoupled from concrete storage technologies.

## Decision
We define abstract repository ports in `src/infra/abstractions/` and select concrete adapters at runtime via the composition root in `src/core/dependencies.py`:
1. **Abstract Port (`OrderRepository`)**: Exposes `save()`, `get()`, `get_all()`, `get_orders_since()`, `get_orders_by_date()`, `count()`, and `get_training_data()` in `src/infra/abstractions/order_repository.py`.
2. **Local / Unit-Test Adapter (`MemoryOrderStore`)**: An in-memory Python dictionary backed by `data/raw_orders.csv` (or synthetic generation fallback) for zero-dependency unit tests and offline CLI runs.
3. **Production Adapter (`PostgresOrderRepository`)**: A SQLAlchemy-backed adapter (`src/infra/database/postgres_order_repository.py`) activated whenever `settings.database_url` targets PostgreSQL (`postgresql://...`), querying the operational ERP `orders` table in deterministic `ORDER BY order_id ASC` order and running the ETL pipeline (row-wise `carrier_capacity` scaling, SHA-256 per-`order_id` deterministic labeling, `clean_orders_data()`, and `validate_dataset()`).
4. **Prediction Persistence (`PredictionStore`)**: Uses `MemoryPredictionStore` locally and `PostgresPredictionStore` in PostgreSQL environments.

## Consequences
* **Positive**:
  * Automated unit and API tests run in milliseconds without requiring an external database server.
  * Switching between local development and production PostgreSQL requires changing only `DATABASE_URL` in configuration, with zero changes to API routers or ML logic.
  * ETL cleaning and validation are consistently enforced at the repository data-extraction boundary.
* **Negative**:
  * `MemoryOrderStore` is non-persistent across process restarts and cannot be shared across multiple worker processes (mitigated in production by using `PostgresOrderRepository`).
