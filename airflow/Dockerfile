# ==============================================================================
# Apache Airflow Orchestrator Image (with isolated app ML virtual environment)
# ==============================================================================
FROM apache/airflow:2.10.5-python3.11

USER root

# Create an isolated venv for src/ ML jobs so Airflow dependencies never conflict
RUN python -m venv /opt/app-venv
COPY requirements-prod.txt /tmp/requirements-prod.txt
RUN /opt/app-venv/bin/pip install --no-cache-dir --upgrade pip setuptools>=80.0.0 wheel>=0.46.2 jaraco.context>=6.1.0 \
    && /opt/app-venv/bin/pip install --no-cache-dir -r /tmp/requirements-prod.txt \
    && rm -f /tmp/requirements-prod.txt \
    && rm -rf /opt/app-venv/lib/python3.11/site-packages/setuptools/_vendor/*.dist-info \
    && groupadd --gid 10001 appgroup \
    && mkdir -p /app/artifacts /app/local_databases /opt/airflow/data \
    && chown -R 50000:10001 /app \
    && chown -R 50000:0 /opt/airflow/data /opt/app-venv \
    && chmod -R 775 /app/artifacts /app/local_databases /opt/airflow/data

COPY --chown=50000:0 src/ /opt/airflow/src/
COPY --chown=50000:0 airflow/dags/ /opt/airflow/dags/

USER airflow
WORKDIR /opt/airflow
