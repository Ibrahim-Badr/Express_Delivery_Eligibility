"""Apache Airflow DAG for Express Delivery ML model retraining orchestration."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator

APP_PYTHON = os.getenv("APP_PYTHON_BIN", "/opt/app-venv/bin/python")
APP_WORKDIR = os.getenv("APP_WORKDIR", "/opt/airflow")
MIN_NEW_ORDERS = os.getenv("RETRAIN_MIN_NEW_ORDERS", "300")
GROWTH_RATIO = os.getenv("RETRAIN_GROWTH_RATIO", "0.05")


def check_new_orders_branch() -> str:
    """Evaluate dynamic hybrid growth trigger via CLI and select DAG branch."""
    env = dict(os.environ)
    env["PYTHONPATH"] = APP_WORKDIR
    result = subprocess.run(
        [
            APP_PYTHON,
            "-m",
            "src.cli",
            "retrain-should-run",
            "--min-new-orders",
            MIN_NEW_ORDERS,
            "--growth-ratio",
            GROWTH_RATIO,
        ],
        cwd=APP_WORKDIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())

    if result.returncode == 0:
        return "retrain_and_promote"
    if result.returncode == 2:
        return "skip_retraining"
    raise RuntimeError(f"retrain-should-run failed with exit code {result.returncode}")


with DAG(
    dag_id="express_delivery_retraining",
    description="Monitors PostgreSQL order growth and executes Champion-Challenger retraining.",
    start_date=datetime(2025, 1, 1),
    schedule="*/2 * * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "mlops",
        "retries": 1,
        "retry_delay": timedelta(seconds=30),
    },
    tags=["mlops", "express-delivery", "retraining"],
) as dag:
    check_new_orders = BranchPythonOperator(
        task_id="check_new_orders",
        python_callable=check_new_orders_branch,
    )

    retrain_and_promote = BashOperator(
        task_id="retrain_and_promote",
        bash_command=(
            f"cd {APP_WORKDIR} && PYTHONPATH={APP_WORKDIR} "
            f"{APP_PYTHON} -m src.cli retrain-check "
            f"--min-new-orders {MIN_NEW_ORDERS} --growth-ratio {GROWTH_RATIO}"
        ),
    )

    skip_retraining = EmptyOperator(task_id="skip_retraining")

    check_new_orders >> [retrain_and_promote, skip_retraining]
