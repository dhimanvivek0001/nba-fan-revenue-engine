"""
Phase 4 — ELT Pipeline DAG.

Orchestrates: synthetic data generation → load Bronze (DuckDB) → dbt run (Silver
staging + intermediate identity resolution) → dbt test. Runs daily; on matchdays
the real-time layer (Phase 9) supplements this with near-real-time Kafka events.

Local dev note: Airflow doesn't run natively on Windows — run this inside the
Airflow container added to docker-compose.yml, or via WSL2. See docs/PHASE_0_SETUP.md.
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import duckdb
import os

PROJECT_ROOT = "/opt/airflow/project"  # mounted path inside the Airflow container
DUCKDB_PATH = f"{PROJECT_ROOT}/data/warehouse/nba_fan_engine.duckdb"
RAW_DATA_DIR = f"{PROJECT_ROOT}/data/raw"

default_args = {
    "owner": "ba_team",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def load_bronze_layer():
    """Load every raw CSV into DuckDB as a bronze_<table> view/table."""
    tables = [
        "fans", "games", "season_ticket_accounts", "ticketmaster_transactions",
        "ticketmaster_customers", "micros_transactions", "email_engagement", "nps_surveys",
    ]
    con = duckdb.connect(DUCKDB_PATH)
    for t in tables:
        csv_path = f"{RAW_DATA_DIR}/{t}.csv"
        con.execute(f"CREATE OR REPLACE TABLE bronze_{t} AS SELECT * FROM read_csv_auto('{csv_path}')")
        cnt = con.execute(f"SELECT COUNT(*) FROM bronze_{t}").fetchone()[0]
        print(f"Loaded bronze_{t}: {cnt:,} rows")
    con.close()


with DAG(
    dag_id="nba_fan_engine_daily_pipeline",
    description="Bronze -> Silver ELT pipeline for the Fan Revenue Intelligence Engine",
    default_args=default_args,
    start_date=datetime(2025, 10, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["nba-fan-engine", "phase4"],
) as dag:

    generate_synthetic_data = BashOperator(
        task_id="generate_synthetic_data",
        bash_command=f"python {PROJECT_ROOT}/data/generate_synthetic_data.py && "
                      f"python {PROJECT_ROOT}/data/generate_ticketmaster_customers.py",
    )

    load_bronze = PythonOperator(
        task_id="load_bronze_layer",
        python_callable=load_bronze_layer,
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {PROJECT_ROOT}/dbt_project && rm -rf target && DBT_PROFILES_DIR=. dbt run --no-partial-parse",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {PROJECT_ROOT}/dbt_project && DBT_PROFILES_DIR=. dbt test --no-partial-parse",
    )

    generate_synthetic_data >> load_bronze >> dbt_run >> dbt_test
