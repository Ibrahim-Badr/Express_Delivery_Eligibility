# ADR 0006: Database Choice (PostgreSQL vs. MongoDB vs. Other)

## Context
The Express Delivery Eligibility application requires an enterprise data source to ingest order streams, train and retrain machine learning models, and serve real-time predictions. The upstream ERP environment (`ERP Pro 2015` simulator in `erp/`) publishes orders targeting relational storage, alongside historical comparisons with **MongoDB** (downstream analytical store) and lightweight local options (**SQLite**):
1. **PostgreSQL** (`postgres:17-alpine`, port `5432`, database `livraison_express`, table `public.orders`): Connected directly to the ERP via bilateral real-time transactional exchange ("Base de production").
2. **MongoDB** (`mongo:8`, port `27017`, database `livraison_express`, collection `orders`): Downstream analytical store containing only 2023+ documents.
3. **SQLite** (`local_databases/local.db`): Single-file embedded SQL engine used strictly as a zero-setup local fallback.

### Technical Comparison

| Dimension | PostgreSQL (`public.orders`) | MongoDB (`orders` collection) | SQLite (Local Fallback) |
| :--- | :--- | :--- | :--- |
| **Architectural Role** | Primary operational production database connected directly to ERP. | Secondary analytical database populated via downstream ETL. | Embedded local database for dev/testing without Docker. |
| **Historical Data Depth** | **Complete history (2015–Present)**: 10,000 legacy records (2015–2022) + 1,000 recent records (2023+) + live stream. | **Truncated history (2023–Present)**: Lacks 8 years of historical order data. | Local synthetic/test records only. |
| **Schema Evolution & ETL** | Preserves historical schema shifts (`weekend` NULL before July 2015; `preparation_time_min` NULL before July 2017), validating ETL imputation. | Pre-cleaned uniform documents from 2023 onwards, masking ingestion edge cases. | Mirrors SQLAlchemy `OrderRecord` schema locally. |
| **Concurrency & ACID** | Full ACID compliance, multi-container concurrent read/write (`erp-simulator`, `trainer`, `airflow`, `api`). | Document-level atomicity, eventual consistency across nodes. | Single-writer file locking; unsuitable for multi-container production. |
| **Cloud Alignment (ADR 0003)** | Matches **Azure Database for PostgreSQL (Flexible Server)**. | Requires Azure Cosmos DB (MongoDB API) or Atlas, fragmenting the stack. | Not applicable to multi-container cloud deployment. |

## Decision
We select **PostgreSQL** as the primary production and test database for orders and predictions (implemented via `PostgresOrderRepository` and `PostgresPredictionStore`), while keeping **SQLite** (`MemoryOrderStore` / local SQLAlchemy) as a lightweight fallback for standalone local unit tests without Docker.

### Rationale:
1. **Authoritative Source of Truth**: Querying PostgreSQL avoids downstream ETL lag and gives the ML trainer access to the complete 2015–present dataset (~11,000+ orders initially).
2. **Real-World ETL Validation**: Historical `NULL` values and scale differences (`carrier_capacity` in `[5, 50]`, English vs. French categories) directly exercise row-wise normalization (`clean_orders_data()`), deterministic per-`order_id` labeling, and `validate_dataset()` at the ingestion boundary, while live ERP batches default to `date.today()` and mirror events to RabbitMQ (`pika`).
3. **Infrastructure Uniformity**: Keeps local Docker Compose (`postgres:17-alpine`) and cloud production (`Azure Database for PostgreSQL`) aligned behind SQLAlchemy and `psycopg[binary]`.

## Consequences
* **Positive**:
  * Maximum historical sample size and diversity for ML training and continuous retraining.
  * Multi-container concurrency between `erp-simulator`, `airflow`, `trainer`, and `api`.
  * Strict decoupling via `OrderRepository` allows adding a `MongoOrderRepository` later without modifying `src/ml/` or `src/api/`.
* **Negative**:
  * Ingestion must systematically clean and impute legacy `NULL` fields and normalize ERP scales before feature transformation.
  * Requires healthcheck coordination (`pg_isready`) in Docker Compose before dependent services query the database.
