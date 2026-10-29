# ADR 0004: Data Source Database Selection (PostgreSQL vs. MongoDB)

## Context
The Express Delivery Eligibility application requires an enterprise data source to ingest order streams, train and retrain machine learning models, and serve real-time predictions. The upstream ERP environment (`ERP Pro 2015` simulator provided in `tp4`) publishes orders to two candidate database targets:
1. **PostgreSQL** (`postgres:17-alpine`, port `5432`, database `livraison_express`, table `public.orders`): Connected directly to the ERP via a bilateral real-time transactional exchange ("Base de production").
2. **MongoDB** (`mongo:8`, port `27017`, database `livraison_express`, collection `orders`): Populated downstream from PostgreSQL via a unilateral ETL pipeline ("Base analytique").

We evaluated both options across data completeness, schema evolution, system architecture, operational complexity, and alignment with our cloud infrastructure.

### Dataset & Technical Comparison

| Dimension | PostgreSQL (`public.orders`) | MongoDB (`orders` collection) |
| :--- | :--- | :--- |
| **Architectural Role** | Primary operational database ("Base de production"). Direct bilateral ERP exchange. | Secondary analytical database ("Base analytique"). Dependent on downstream ETL. |
| **Historical Data Depth** | **Complete history (2015 – Present)**: 10,000 legacy records (2015–2022) + 1,000 shared recent records (2023–present) + continuous live stream. | **Truncated history (2023 – Present)**: Only 1,000 shared records + continuous live stream. Lacks 8 years of historical orders. |
| **Schema Evolution & Migrations** | Contains historical schema migrations (`weekend` is `NULL` before July 2015; `preparation_time_min` is `NULL` before July 2017). | Cleaned uniform documents from 2023 onwards (all fields populated). Does not exercise legacy data migration handling. |
| **ETL & Data Quality Testing** | Actively exercises cleaning, imputation, and validation rules (handling legacy `NULL`s, out-of-range anomalies, and migrations). | Bypasses historical null-handling validation, masking potential data ingestion defects. |
| **Consistency & Constraints** | ACID transactional consistency, primary key enforcement (`order_id`), strict relational types. | Document-level atomicity, schema-flexible, eventual consistency across distributed nodes. |
| **Cloud Alignment (ADR 0001)** | Directly matches our deployment decision: **Azure Database for PostgreSQL (Flexible Server)**. | Requires introducing Azure Cosmos DB (MongoDB API) or Mongo Atlas, increasing cloud stack fragmentation. |
| **Application Dependency** | Standard relational driver (`psycopg[binary]`), already aligned with modern Python async/sync ecosystem. | Additional NoSQL driver (`pymongo`) required solely for order ingestion. |

## Decision
We select **PostgreSQL** as the primary source database for the Express Delivery Eligibility system, implemented behind the abstract `OrderRepository` / `OrderStore` interface.

### Rationale:
1. **Authoritative Source of Truth**: PostgreSQL is the primary operational database directly integrated with `ERP Pro 2015`. Querying PostgreSQL avoids replication lag, synchronization failures, and potential transformation bias introduced by downstream ETL processes.
2. **Comprehensive Historical Data for ML**: PostgreSQL provides the complete historical dataset dating back to January 2015 (~11,000+ orders initially), providing ample statistical diversity for robust model training and cross-validation, unlike MongoDB's truncated 2023+ window.
3. **Data Quality & ETL Validation**: Real-world data is inherently imperfect. The historical `NULL` values in PostgreSQL (`weekend`, `preparation_time_min`) explicitly test and enforce our automated data cleaning and imputation pipeline (`clean_orders_data`, `validate_dataset`), satisfying the core project requirement: *"Never trust raw data quality; validate and clean at the ingestion boundary"*.
4. **Cloud & Architectural Coherence (ADR 0001)**: ADR 0001 established Azure Database for PostgreSQL (Flexible Server) as our managed production database. Using PostgreSQL maintains complete architectural uniformity between local development, Docker Compose, CI/CD, and production environments without introducing supplementary NoSQL services.
5. **Clean Architecture Decoupling**: In accordance with the Dependency Inversion Principle (DIP), domain logic and API routers interact exclusively with the `OrderRepository` abstraction (`save()`, `get()`, `get_all()`, `get_training_data()`). Concrete persistence is encapsulated in `PostgresOrderRepository`. Should a specialized analytical use case require MongoDB in the future, a `MongoOrderRepository` can be added without altering business or ML logic.

## Consequences
* **Positive**:
  * Direct access to the authoritative transactional ERP records.
  * Maximum historical sample size for model training and feature engineering.
  * Full validation of the ETL cleaning and imputation pipeline on production-grade schema migrations.
  * Perfect consistency with the Azure cloud infrastructure defined in ADR 0001.
  * Strict decoupling via Clean Architecture repository pattern.
* **Negative**:
  * Ingestion logic must systematically handle historical `NULL` values through robust imputation before feature transformation.
  * Connection pool management (`psycopg`) must be configured properly in containerized environments.
